"""Resolve inherited protocol references iteratively.

Consumes ExtractedProtocol objects (from protocol_extractor) and enriches
protocol_text by replacing inherited context phrases with fragments fetched from
ancestor papers.

Uses the same client order as FullTextRetriever and reuses TextExtractor logic
for raw->plain conversion.
"""
from __future__ import annotations

import contextlib
import json
import logging
import re
from typing import Optional

import httpx

from config import get_settings
from api_clients import (
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    PMCClient,
    SemanticScholarClient,
    UnpaywallClient,
)
from models.paper import Paper
from models.protocol import ExtractedProtocol, InheritedReference
from processors.text_extractor import TextExtractor

logger = logging.getLogger(__name__)
_s = get_settings()

_RESOLVE_SYSTEM = """You are a biomedical protocol resolution assistant.

Inputs:
- The full text of the current protocol.
- A context phrase in the current protocol, that references to a parent paper.
- The full text of the parent paper.

Objective:
Find and return the text from the parent paper that best resolves the context phrase in the current protocol, 
so that a researcher could understand and execute the protocol without needing to read the parent paper.

Rules:
- Return an empty `resolved_fragment` if no reliable text exists.
- Use only text from the provided parent full text; do not infer or paraphrase.
- If the text extracted from the parent paper contains references, maintain them verbatim in the resolved fragment.
"""

_RESOLVE_SCHEMA: dict = {
    "name": "resolved_reference_fragment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "resolved_fragment": {"type": "string"},
        },
        "required": ["resolved_fragment"],
        "additionalProperties": False,
    },
}


class ReferenceResolver:
    """Resolve inherited references recursively (max 3 levels by default)."""

    _CLIENT_ORDER = [
        ElsevierClient,
        EuropePMCClient,
        PMCClient,
        OpenAlexClient,
        SemanticScholarClient,
        UnpaywallClient,
    ]

    def __init__(self, max_depth: int = 3) -> None:
        self._max_depth = max_depth
        self._text_extractor = TextExtractor()
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

    async def resolve_all(self, protocols: list[ExtractedProtocol]) -> list[ExtractedProtocol]:
        """Resolve refs for protocols with score >= 60 and return enriched list."""
        logger.info("Step 8 start - Reference resolution on %d extracted protocols.", len(protocols))
        eligible_protocols = [p for p in protocols if p.relevance_score >= 60]
        discarded = len(protocols) - len(eligible_protocols)
        if discarded:
            logger.info(
                "Step 8 filter: discarded %d protocols with relevance_score < 60.",
                discarded,
            )

        async with contextlib.AsyncExitStack() as stack:
            clients = [await stack.enter_async_context(cls()) for cls in self._CLIENT_ORDER]
            for protocol in eligible_protocols:
                await self._resolve_protocol(protocol, clients)
        logger.info("Step 8 complete - Processed %d eligible protocols.", len(eligible_protocols))
        return eligible_protocols

    async def _resolve_protocol(self, protocol: ExtractedProtocol, clients: list) -> None:
        # Breadth-first traversal of inherited references.
        # Each item is (reference_to_resolve, depth_level).
        queue: list[tuple[InheritedReference, int]] = [
            (ref, 1) for ref in protocol.inherited_references
        ]
        # Prevent repeated work and infinite loops across cross-citations.
        seen: set[tuple[str, str]] = set()

        while queue:
            ref, depth = queue.pop(0)
            if depth > self._max_depth:
                continue

            seen_key = (ref.target_doi.lower(), ref.context_phrase.lower())
            if seen_key in seen:
                continue
            seen.add(seen_key)

            parent_plain = await self._fetch_plain_text(ref.target_doi, clients)
            if not parent_plain:
                continue

            fragment = await self._select_fragment_with_llm(
                protocol_text=protocol.protocol_text,
                context_phrase=ref.context_phrase,
                target_ref=ref.target_doi,
                parent_text=parent_plain,
            )
            if not fragment:
                continue

            protocol.protocol_text = _merge_fragment(
                protocol.protocol_text,
                ref.context_phrase,
                fragment,
                ref.target_doi,
            )
            ref.resolved_fragment = fragment
            ref.resolution_depth = depth

            if depth < self._max_depth:
                # Recursively expand into ancestor-of-ancestor references.
                # We support direct DOI/PMCID, and numeric citations mapped
                # through the parent paper references section.
                nested = _discover_nested_targets(fragment, parent_plain)
                for target_ref in nested:
                    queue.append(
                        (
                            InheritedReference(
                                context_phrase=fragment[:220],
                                target_doi=target_ref,
                            ),
                            depth + 1,
                        )
                    )

    async def _fetch_plain_text(self, target_ref: str, clients: list) -> Optional[str]:
        """Fetch parent full text from a target reference and convert to plain text.

        Supports DOI and PMCID targets. Other identifiers are skipped.
        """
        normalized_doi = _extract_first_doi(target_ref)
        normalized_pmcid = _extract_first_pmcid(target_ref)
        if not normalized_doi and not normalized_pmcid:
            return None

        paper = Paper(
            doi=normalized_doi,
            title="Inherited source",
            authors=[],
            abstract=None,
            year=None,
            source="inherited_protocol_resolution",
            url=(
                f"https://www.ncbi.nlm.nih.gov/pmc/articles/{normalized_pmcid}/"
                if normalized_pmcid
                else None
            ),
        )

        for client in clients:
            try:
                ft = await client.fetch_full_text(paper)  # type: ignore[attr-defined]
                if ft is None or not ft.content.strip():
                    continue

                work = paper.model_copy(deep=True)
                work.full_text = ft
                converted = self._text_extractor.extract_all([work])
                if converted and converted[0].full_text and converted[0].full_text.content.strip():
                    return converted[0].full_text.content
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Inherited fetch failed for ref %s via %s: %s",
                    target_ref,
                    type(client).__name__,
                    exc,
                )

        return None

    async def _select_fragment_with_llm(
        self,
        protocol_text: str,
        context_phrase: str,
        target_ref: str,
        parent_text: str,
    ) -> Optional[str]:
        """Ask the LLM to select the exact parent-text fragment to insert."""
        user_prompt = (
            f"Target reference: {target_ref}\n"
            f"Context phrase in current protocol:\n{context_phrase}\n\n"
            "Current protocol text:\n"
            f"{protocol_text}\n\n"
            "Parent paper full text (already extracted/cleaned):\n"
            f"{parent_text}"
        )

        payload = {
            "model": _s.gemini_model_fulltext,
            "messages": [
                {"role": "system", "content": _RESOLVE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _RESOLVE_SCHEMA},
        }

        try:
            async with httpx.AsyncClient(timeout=_s.http_timeout * 2) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
                if resp.is_error:
                    logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                    resp.raise_for_status()

            raw = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(raw)
            fragment = (data.get("resolved_fragment") or "").strip()
            if not fragment:
                return None
            return re.sub(r"\s{2,}", " ", fragment)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM fragment selection failed for ref %s and context '%s': %s",
                target_ref,
                context_phrase,
                exc,
            )
            return None


def _merge_fragment(protocol_text: str, context_phrase: str, fragment: str, target_ref: str) -> str:
    infill = f"{context_phrase} [Resolved from ref {target_ref}: {fragment}]"
    pattern = re.compile(re.escape(context_phrase), re.IGNORECASE)
    if pattern.search(protocol_text):
        return pattern.sub(infill, protocol_text, count=1)
    return protocol_text + "\n\n" + infill


def _discover_nested_targets(fragment: str, parent_text: str) -> list[str]:
    """Discover nested inherited targets from fragment and parent references.

    Strategy:
    1) Take direct DOI/PMCID identifiers in the resolved fragment.
    2) If fragment uses numeric citations (e.g., [12], [4-6]), map those markers
       to reference lines in the parent text and extract DOI/PMCID from there.
    """
    out: list[str] = []
    seen: set[str] = set()

    def _add(values: list[str]) -> None:
        for value in values:
            k = value.lower()
            if k not in seen:
                seen.add(k)
                out.append(value)

    _add(_extract_identifiers(fragment))

    citation_nums = _extract_numeric_citations(fragment)
    if citation_nums:
        ref_lines = _find_reference_lines(parent_text, citation_nums)
        for line in ref_lines:
            _add(_extract_identifiers(line))

    return out


def _extract_identifiers(text: str) -> list[str]:
    """Extract fetchable reference identifiers (DOI and PMCID)."""
    ids: list[str] = []
    seen: set[str] = set()

    doi_re = re.compile(r"10\.\d{4,9}/[^\s\]\[\)\(\"'<>]+", re.IGNORECASE)
    for m in doi_re.finditer(text):
        doi = m.group(0).rstrip(".,;:)")
        key = doi.lower()
        if key not in seen:
            seen.add(key)
            ids.append(doi)

    pmcid_re = re.compile(r"PMC\d+", re.IGNORECASE)
    for m in pmcid_re.finditer(text):
        pmcid = m.group(0).upper()
        key = pmcid.lower()
        if key not in seen:
            seen.add(key)
            ids.append(pmcid)

    return ids


def _extract_numeric_citations(text: str) -> set[int]:
    """Extract numeric citation indices from inline markers like [12] or [3-5, 9]."""
    nums: set[int] = set()
    # Matches [12], [3-6], [2, 5, 9-11]
    bracket_re = re.compile(r"\[(\d{1,4}(?:\s*[-,]\s*\d{1,4})*)\]")
    for match in bracket_re.finditer(text):
        raw = match.group(1)
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        for part in parts:
            if "-" in part:
                bounds = [x.strip() for x in part.split("-", 1)]
                if len(bounds) != 2 or not bounds[0].isdigit() or not bounds[1].isdigit():
                    continue
                start = int(bounds[0])
                end = int(bounds[1])
                if 0 < start <= end and (end - start) <= 50:
                    nums.update(range(start, end + 1))
            elif part.isdigit():
                val = int(part)
                if val > 0:
                    nums.add(val)
    return nums


def _find_reference_lines(parent_text: str, citation_numbers: set[int]) -> list[str]:
    """Find candidate reference entries for numeric citation numbers."""
    if not citation_numbers:
        return []

    lines = [ln.strip() for ln in parent_text.splitlines() if ln.strip()]
    if not lines:
        return []

    refs_start = 0
    for idx, line in enumerate(lines):
        l = line.lower()
        if l == "references" or l.startswith("references ") or l.startswith("references:"):
            refs_start = idx
            break

    selected: list[str] = []
    selected_seen: set[str] = set()
    for citation_num in sorted(citation_numbers):
        num_prefixes = _citation_prefix_patterns(citation_num)
        for line in lines[refs_start:]:
            if any(rx.search(line) for rx in num_prefixes):
                key = line.lower()
                if key not in selected_seen:
                    selected_seen.add(key)
                    selected.append(line)
                break

    return selected


def _extract_first_doi(text: str) -> Optional[str]:
    """Return the first DOI found in text, if present."""
    ids = _extract_identifiers(text)
    for value in ids:
        if value.upper().startswith("PMC"):
            continue
        return value
    return None


def _extract_first_pmcid(text: str) -> Optional[str]:
    """Return the first PMCID found in text, if present."""
    ids = _extract_identifiers(text)
    for value in ids:
        if value.upper().startswith("PMC"):
            return value.upper()
    return None


def _citation_prefix_patterns(citation_num: int) -> list[re.Pattern[str]]:
    """Common numbered-reference prefixes: [12], 12., 12), or '12 '."""
    return [
        re.compile(rf"^\[\s*{citation_num}\s*\]"),
        re.compile(rf"^{citation_num}[\.)]\s"),
        re.compile(rf"^{citation_num}\s"),
    ]


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import (
        STEP7_FILE,
        STEP8_FILE,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        print("[Step 8] START | Solve Inherited References")
        protocols = load_model_list(STEP7_FILE, ExtractedProtocol)
        resolved = await ReferenceResolver(max_depth=3).resolve_all(protocols)
        save_json(resolved, STEP8_FILE)
        print(f"Processed {len(resolved)} protocols with score >= 60 for reference resolution.")
        print(
            f"[Step 8] DONE | input={len(protocols)} output={len(resolved)} | Output: intermediate_outputs/{STEP8_FILE}"
        )

    asyncio.run(_main())
