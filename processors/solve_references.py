"""Resolve inherited protocol references iteratively.

Consumes ExtractedProtocol objects (from protocol_extractor) and enriches
protocol_text by replacing inherited context phrases with fragments fetched from
ancestor papers.

Uses the same client order as FullTextRetriever and reuses TextExtractor logic
for raw->plain conversion.

PERFORMANCE OPTIMIZATIONS:
- Parallel protocol processing with semaphore-controlled concurrency
- In-memory cache for fetched papers to avoid duplicate fetches
- Batch LLM calls with connection pooling
- Early termination on failed fetches
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
from typing import Optional

import httpx

from config import get_settings
from api_clients import (
    CrossRefClient,
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    PMCClient,
    ScopusClient,
    SemanticScholarClient,
    UnpaywallClient,
)
from models.paper import Paper
from models.protocol import ExtractedProtocol, InheritedReference
from processors.text_extractor import TextExtractor
from utils.intermediate_io import STEP6_FILE, load_model_list

logger = logging.getLogger(__name__)
_s = get_settings()

_RESOLVE_SYSTEM = """You are a laboratory protocol resolution assistant.

**Inputs:**
1. `protocol_fragment`: A fragment from a lab protocol
2. `context_phrase`: A specific phrase in the fragment that references a parent paper's methodology
3. `parent_paper_text`: The full text of the parent paper

**Objective:**
Extract the relevant methodological details from the parent paper that resolve the context phrase, 
enabling a researcher to execute the protocol without consulting the original parent paper.

**Extraction Rules:**
- Extract verbatim from parent paper, do not infer or paraphrase; include reagents, equipment, conditions, and all procedural steps.
- Return an empty `resolved_fragment` if the parent paper does not contain details about the technique needed.
- Combine non-contiguous sections if needed, prioritize Methods section.

Output must contain only one key:
- `resolved_fragment`

"""
# **Nested References**
# - Add nested references when the "how-to" of a step is offloaded to another document.
# - If the `resolved_fragment` extracted from the parent paper contains nested inherited references like 'We performed RNA-seq as described in Smith et al.', return nested references as objects with:
#     - `nested_context_phrase`: exact phrase from the resolved fragment that indicates inherited context.
#     - `target_doi`: DOI if explicitly present (or null).
#     - `target_title`: if DOI is not present, return the title if available (or null).
#     - `target_year`: publication year if available (or null).
# - Include in nested references ONLY IF the cited source is required to physically replicate a laboratory action (e.g., "prepared as described in...", "assayed following...") AND is indispensable for the protocol.
# - Exclude references to: software and algorithms (e.g., "analyzed with ImageJ"), databases and IDs (e.g., "protein interactions were retrieved from STRING") and statistical tests (e.g., "significance was assessed by ANOVA").
# - Return an empty list for `nested_references` when none are reliably identifiable.

# **Example:**
# - Context phrase: "We performed RNA-seq as described in Smith et al."
# - Resolved fragment: Total RNA was extracted using the RNeasy kit (Qiagen) and libraries were prepared with the NEBNext Ultra II kit, following the manufacturer's instructions. Before sequencing, a PCR was performed as previously described (Buenrostro et al. 2015)."

# Output:
# {
#   "resolved_fragment": "Total RNA was extracted using the RNeasy kit (Qiagen) and libraries were prepared with the NEBNext Ultra II kit, following the manufacturer's instructions. Before sequencing, a PCR was performed as previously described (Buenrostro et al. 2015)."
#   "nested_references": [
#     {
#       "nested_context_phrase": "Before sequencing, a PCR was performed as previously described (Buenrostro et al. 2015).",
#       "target_doi": null,
#             "target_title": "NEBNext Ultra II Directional RNA Library Prep Kit Protocol",
#             "target_year": null
#     }
#   ]
# }
# """

_RESOLVE_SCHEMA: dict = {
    "name": "resolved_reference_fragment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "resolved_fragment": {"type": "string"},
            # Nested references are temporarily disabled.
            # Keep this schema block commented to re-enable later.
            # "nested_references": {
            #     "type": "array",
            #     "items": {
            #         "type": "object",
            #         "properties": {
            #             "nested_context_phrase": {"type": "string"},
            #             "target_doi": {"type": ["string", "null"]},
            #             "target_title": {"type": ["string", "null"]},
            #             "target_year": {"type": ["integer", "null"]},
            #         },
            #         "required": ["nested_context_phrase"],
            #         "additionalProperties": False,
            #     },
            # },
        },
        "required": ["resolved_fragment"],
        "additionalProperties": False,
    },
}

# Regex patterns compiled once
_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\]\[\)\(\"'<>]+", re.IGNORECASE)
_DOI_PREFIX_PATTERN = re.compile(
    r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", flags=re.IGNORECASE
)


class ReferenceResolver:
    """Resolve inherited references recursively (max 3 levels by default)."""

    FT_CLIENT_ORDER = [
        ElsevierClient,
        EuropePMCClient,
        PMCClient,
        UnpaywallClient,
        SemanticScholarClient,
        OpenAlexClient,
    ]

    SEARCH_CLIENT_ORDER = [
        EuropePMCClient,
        SemanticScholarClient,
        ElsevierClient,
        CrossRefClient,
        OpenAlexClient,
        ScopusClient,
    ]

    def __init__(
        self,
        max_depth: Optional[int] = None,
        max_concurrent_protocols: int = 10,
        max_concurrent_fetches: int = 5,
    ) -> None:
        self._max_depth = _s.max_citation_depth if _s.max_citation_depth is not None else max_depth
        self._text_extractor = TextExtractor()
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }
        
        # Concurrency control
        self._protocol_semaphore = asyncio.Semaphore(max_concurrent_protocols)
        self._fetch_semaphore = asyncio.Semaphore(max_concurrent_fetches)
        
        # Cache for fetched papers (key: ref_key, value: plain_text or None)
        self._paper_cache: dict[str, Optional[str]] = {}
        # Step 6 full-text reuse cache keyed by canonical DOI
        self._step6_fulltext_by_doi: dict[str, str] = {}
        # Step 6 full-text reuse cache keyed by normalized title
        self._step6_fulltext_by_title: dict[str, str] = {}
        self._step6_cache_loaded = False
        self._paper_cache_hits = 0
        self._min_chars = _s.full_text_min_chars
        self._max_chars = _s.full_text_max_chars
        
        # Shared HTTP client for LLM calls (connection pooling)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def resolve_all(
        self, protocols: list[ExtractedProtocol]
    ) -> list[ExtractedProtocol]:
        """Resolve inherited references for protocols with relevance_score >= 70."""
        logger.info(
            "Step 8 start - Reference resolution on %d extracted protocols.",
            len(protocols),
        )
        eligible_protocols = [p for p in protocols if p.relevance_score >= 70]
        discarded = len(protocols) - len(eligible_protocols)
        if discarded:
            logger.info(
                "Step 8 filter: discarded %d protocols with relevance_score < 70.",
                discarded,
            )

        self._load_step6_fulltext_cache()

        # Initialize shared HTTP client
        self._http_client = httpx.AsyncClient(
            timeout=_s.http_timeout,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        try:
            async with contextlib.AsyncExitStack() as stack:
                ft_clients = [
                    await stack.enter_async_context(cls()) for cls in self.FT_CLIENT_ORDER
                ]
                search_clients = [
                    await stack.enter_async_context(cls()) for cls in self.SEARCH_CLIENT_ORDER
                ]
                
                # Process protocols in parallel
                tasks = [
                    self._resolve_protocol_with_semaphore(
                        protocol,
                        ft_clients,
                        search_clients,
                    )
                    for protocol in eligible_protocols
                ]
                await asyncio.gather(*tasks)
        finally:
            if self._http_client:
                await self._http_client.aclose()

        logger.info(
            "Step 8 complete - Processed %d eligible protocols (cache hits: %d, cache size: %d).",
            len(eligible_protocols),
            self._paper_cache_hits,
            len(self._paper_cache),
        )
        return eligible_protocols

    def _load_step6_fulltext_cache(self) -> None:
        """Load DOI->plain full-text entries from Step 6 output when available."""
        if self._step6_cache_loaded:
            return
        
        try:
            papers = load_model_list(STEP6_FILE, Paper)
            self._step6_cache_loaded = True

        except FileNotFoundError:
            logger.info("Step 6 file not found; inherited resolution will fetch full text on demand.")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load Step 6 full-text cache: %s", exc)
            return

        loaded_doi = 0
        loaded_title = 0
        for paper in papers:
            if not paper.full_text:
                continue
            content = (paper.full_text.content or "").strip()
            if not self._is_within_length_bounds(content):
                continue

            doi_key = _normalize_doi(paper.doi) if paper.doi else ""
            if doi_key and doi_key not in self._step6_fulltext_by_doi:
                self._step6_fulltext_by_doi[doi_key] = content
                loaded_doi += 1

            title_key = _normalize_title(paper.title)
            if title_key and title_key not in self._step6_fulltext_by_title:
                self._step6_fulltext_by_title[title_key] = content
                loaded_title += 1

        logger.info(
            "Step 8 cache ready - loaded %d DOI entries and %d title entries from %s.",
            loaded_doi,
            loaded_title,
            STEP6_FILE,
        )

    async def _resolve_protocol_with_semaphore(
        self,
        protocol: ExtractedProtocol,
        ft_clients: list,
        search_clients: list,
    ) -> None:
        """Wrapper to control concurrency for protocol processing."""
        async with self._protocol_semaphore:
            await self._resolve_protocol(protocol, ft_clients, search_clients)

    async def _resolve_protocol(
        self,
        protocol: ExtractedProtocol,
        ft_clients: list,
        search_clients: list,
    ) -> None:
        """Resolve inherited references without recursive expansion."""
        # Queue: (reference, depth, context_text_for_resolution)
        queue: list[tuple[InheritedReference, int, str]] = [
            (ref, 1, protocol.protocol_text) for ref in protocol.inherited_references
        ]

        # Track processed references to avoid cycles and duplicates
        seen: set[tuple[str, str]] = set()
        # Recursive queue expansion is temporarily disabled.
        # Keep this set declaration commented to re-enable nested traversal later.
        # known_refs: set[tuple[str, str]] = {
        #     (_get_ref_key(ref), ref.context_phrase.lower())
        #     for ref in protocol.inherited_references
        # }

        while queue:
            ref, depth, resolver_context_text = queue.pop(0)
            if depth > self._max_depth:
                continue

            # Skip if already processed
            seen_key = (_get_ref_key(ref), ref.context_phrase.lower())
            if seen_key in seen:
                continue
            seen.add(seen_key)

            # Fetch parent paper text (with caching)
            parent_plain = await self._fetch_plain_text_cached(
                ref,
                ft_clients,
                search_clients,
            )
            if not parent_plain:
                continue

            # Extract only the direct resolved fragment (nested references disabled).
            fragment = await self._select_fragment_with_llm(
                protocol_text=resolver_context_text,
                context_phrase=ref.context_phrase,
                target_ref=_format_ref_display(ref),
                parent_text=parent_plain,
            )
            if not fragment:
                continue

            # Update protocol text with resolved fragment
            protocol.protocol_text = _merge_fragment(
                protocol.protocol_text,
                ref.context_phrase,
                fragment,
                _format_ref_display(ref),
            )
            ref.resolved_fragment = fragment
            ref.resolution_depth = depth

            # Recursive queue expansion is temporarily disabled.
            # Keep this block commented to restore nested reference resolution later.
            # if depth < self._max_depth:
            #     for nested_ref in nested_refs:
            #         nested_key = (
            #             _get_ref_key(nested_ref),
            #             nested_ref.context_phrase.lower(),
            #         )
            #         if nested_key not in known_refs:
            #             known_refs.add(nested_key)
            #             protocol.inherited_references.append(nested_ref)
            #             queue.append((nested_ref, depth + 1, fragment))

    async def _fetch_plain_text_cached(
        self,
        reference: InheritedReference,
        ft_clients: list,
        search_clients: list,
    ) -> Optional[str]:
        """Fetch with caching to avoid duplicate fetches."""
        cache_key = _get_ref_key(reference)
        
        # Check cache
        if cache_key in self._paper_cache:
            return self._paper_cache[cache_key]
        
        # Fetch with semaphore control
        async with self._fetch_semaphore:
            # Double-check cache (another task might have fetched while waiting)
            if cache_key in self._paper_cache:
                return self._paper_cache[cache_key]
            
            result = await self._fetch_plain_text(
                reference,
                ft_clients,
                search_clients,
            )
            self._paper_cache[cache_key] = result
            return result

    async def _fetch_plain_text(
        self,
        reference: InheritedReference,
        ft_clients: list,
        search_clients: list,
    ) -> Optional[str]:
        """Fetch parent full text from a target reference and convert to plain text.

        Supports DOI targets directly.
        Falls back to title-based exact-match search when DOI is missing.
        """
        normalized_doi = _extract_first_doi(reference.target_doi or "")
        normalized_title = _normalize_title(reference.target_title or "")

        if normalized_doi:
            cached = self._step6_fulltext_by_doi.get(_normalize_doi(normalized_doi))
            if cached:
                self._paper_cache_hits += 1
                return cached

        if normalized_title:
            cached = self._step6_fulltext_by_title.get(normalized_title)
            if cached:
                self._paper_cache_hits += 1
                return cached

        # Create Paper object if we have DOI
        if normalized_doi:
            paper = Paper(
                doi=normalized_doi,
                title=reference.target_title or "Inherited source",
                authors=[],
                year=None,
                abstract=None,
                source="inherited_protocol_resolution",
                url=None,
            )
        else:
            # Try title-based search
            paper = await self._search_by_title(reference, search_clients)
            # Update DOI if found via title search
            if paper and paper.doi:
                reference.target_doi = paper.doi

        if not paper:
            return None

        if paper.doi:
            cached = self._step6_fulltext_by_doi.get(_normalize_doi(paper.doi))
            if cached:
                self._paper_cache_hits += 1
                return cached

        paper_title_key = _normalize_title(paper.title)
        if paper_title_key:
            cached = self._step6_fulltext_by_title.get(paper_title_key)
            if cached and self._is_within_length_bounds(cached):
                self._paper_cache_hits += 1
                return cached

        # Try each client to fetch full text
        return await self._fetch_and_extract_text(paper, ft_clients)

    async def _fetch_and_extract_text(
        self, paper: Paper, clients: list
    ) -> Optional[str]:
        """Attempt to fetch and extract plain text from paper using available clients.
        
        Uses fail-fast approach - tries clients in order and returns on first success.
        """
        for client in clients:
            try:
                ft = await client.fetch_full_text(paper)  # type: ignore[attr-defined]
                if not ft or not ft.content.strip():
                    continue

                # Convert to plain text
                work = paper.model_copy(deep=True)
                work.full_text = ft
                converted = self._text_extractor.extract_all([work])
                if (
                    converted
                    and converted[0].full_text
                    and converted[0].full_text.content.strip()
                    and self._is_within_length_bounds(converted[0].full_text.content)
                ):
                    return converted[0].full_text.content
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Inherited fetch failed via %s: %s",
                    type(client).__name__,
                    exc,
                )
                # Continue to next client instead of failing completely
                continue

        return None

    def _is_within_length_bounds(self, text: str) -> bool:
        """Return True when text length matches configured Step 6 bounds."""
        text_len = len(text)
        return self._min_chars <= text_len <= self._max_chars

    async def _search_by_title(
        self,
        reference: InheritedReference,
        clients: list,
    ) -> Optional[Paper]:
        """Search by title using deterministic, score-free matching rules.
        
        Runs searches in parallel for speed.
        """
        title = (reference.target_title or "").strip()
        if not title:
            return None

        # Gather search results from all capable clients in parallel
        search_clients = [c for c in clients if hasattr(c, "search")]
        if not search_clients:
            return None
            
        tasks = [
            c.search(title, max_results=2)  # type: ignore[attr-defined]
            for c in search_clients
        ]

        candidates: list[Paper] = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for item in results:
            if not isinstance(item, Exception):
                candidates.extend(item)

        if not candidates:
            return None

        # Deduplicate candidates
        deduped = _deduplicate_papers(candidates)
        if not deduped:
            return None

        # Find best match
        return _find_best_title_match(title, deduped, reference.target_year)

    async def _select_fragment_with_llm(
        self,
        protocol_text: str,
        context_phrase: str,
        target_ref: str,
        parent_text: str,
    ) -> Optional[str]:
        """Ask the LLM to select only the direct fragment to insert.
        
        Uses shared HTTP client for connection pooling.
        """
 
        user_prompt = (
            f"Current protocol fragment:\n{protocol_text}\n\n"
            f"Context phrase in current protocol fragment:\n{context_phrase}\n\n"
            f"Parent paper full text:\n{parent_text}"
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
            resp = await self._http_client.post(  # type: ignore[union-attr]
                f"{self._base}/chat/completions",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()

            data = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(data)

            fragment = (parsed.get("resolved_fragment") or "").strip()

            if not fragment:
                return None

            # Normalize whitespace
            fragment = re.sub(r"\s{2,}", " ", fragment)
            return fragment

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "LLM fragment selection failed for ref %s and context '%s': %s",
                target_ref,
                context_phrase,
                exc,
            )
            return None


# Helper functions

def _merge_fragment(
    protocol_text: str, context_phrase: str, fragment: str, target_ref: str
) -> str:
    """Merge resolved fragment into protocol text at context phrase location."""
    infill = f"{context_phrase} [Resolved from ref {target_ref}: {fragment}]"
    pattern = re.compile(re.escape(context_phrase), re.IGNORECASE)

    if pattern.search(protocol_text):
        # Replace first occurrence, treating backslashes literally
        return pattern.sub(lambda _: infill, protocol_text, count=1)

    return f"{protocol_text}\n\n{infill}"


def _extract_identifiers(text: str) -> list[str]:
    """Extract fetchable DOI identifiers."""
    ids: list[str] = []
    seen: set[str] = set()

    # Extract DOIs
    for match in _DOI_PATTERN.finditer(text):
        doi = match.group(0).rstrip(".,;:)")
        if doi.lower() not in seen:
            seen.add(doi.lower())
            ids.append(doi)

    return ids


def _extract_first_doi(text: str) -> Optional[str]:
    """Return the first DOI found in text, if present."""
    for identifier in _extract_identifiers(text):
        return identifier
    return None


def _get_ref_key(reference: InheritedReference) -> str:
    """Get unique key for reference (DOI or title)."""
    return (
        _normalize_doi(reference.target_doi or "")
        or _normalize_title(reference.target_title or "")
        or ""
    )


def _format_ref_display(reference: InheritedReference) -> str:
    """Format reference for display."""
    if reference.target_doi:
        return reference.target_doi

    parts = []
    if reference.target_title:
        parts.append(reference.target_title)
    if reference.target_year is not None:
        parts.append(str(reference.target_year))

    return " | ".join(parts) if parts else "unknown reference"


def _deduplicate_papers(papers: list[Paper]) -> list[Paper]:
    """Deduplicate papers by DOI first, then by normalized title."""
    if not papers:
        return []

    # Group by DOI, keeping most complete
    doi_best: dict[str, Paper] = {}
    no_doi: list[Paper] = []

    for paper in papers:
        if paper.doi:
            key = _normalize_doi(paper.doi)
            if key not in doi_best or _paper_score(paper) > _paper_score(
                doi_best[key]
            ):
                doi_best[key] = paper
        else:
            no_doi.append(paper)

    # Deduplicate by normalized title
    title_best: dict[str, Paper] = {}
    for paper in [*doi_best.values(), *no_doi]:
        norm_title = _normalize_title(paper.title)
        if not norm_title:
            continue
        if norm_title not in title_best or _paper_score(paper) > _paper_score(
            title_best[norm_title]
        ):
            title_best[norm_title] = paper

    return list(title_best.values())


def _find_best_title_match(
    target_title: str,
    candidates: list[Paper],
    target_year: Optional[int] = None,
) -> Optional[Paper]:
    """Find best matching paper by title using hierarchical matching."""
    wanted_norm = _normalize_title(target_title)
    if not wanted_norm:
        return None

    # First filter by reference year when available; fallback to all candidates if none match.
    if target_year is not None:
        year_filtered = [p for p in candidates if p.year == target_year]
        if year_filtered:
            candidates = year_filtered

    # 1. Exact normalized match
    exact = [p for p in candidates if _normalize_title(p.title) == wanted_norm]
    if exact:
        return _select_most_complete(exact)

    # 2. Containment match (one title contains the other)
    containment = [
        p
        for p in candidates
        if _normalize_title(p.title) in wanted_norm
        or wanted_norm in _normalize_title(p.title)
    ]
    if containment:
        return _select_most_complete(containment)

    # 3. Token subset match
    wanted_tokens = _get_title_tokens(target_title)
    if not wanted_tokens:
        return None

    token_matches = [
        p
        for p in candidates
        if _get_title_tokens(p.title)
        and (
            wanted_tokens.issubset(_get_title_tokens(p.title))
            or _get_title_tokens(p.title).issubset(wanted_tokens)
        )
    ]
    if token_matches:
        return _select_most_complete(token_matches)

    return None


def _select_most_complete(papers: list[Paper]) -> Optional[Paper]:
    """Select the most complete paper from a list, or None if tie."""
    if not papers:
        return None

    if len(papers) == 1:
        return papers[0]

    sorted_papers = sorted(papers, key=_paper_score, reverse=True)

    # Return None if top two have same score (ambiguous)
    if len(sorted_papers) >= 2 and _paper_score(sorted_papers[0]) == _paper_score(
        sorted_papers[1]
    ):
        return None

    return sorted_papers[0]


def _paper_score(paper: Paper) -> int:
    """Calculate completeness score for a paper."""
    score = 0
    if paper.doi:
        score += 1
    if paper.title:
        score += 1
    if paper.abstract:
        score += 3
    if paper.authors:
        score += min(len(paper.authors), 10)
    if paper.year:
        score += 1
    if paper.url:
        score += 1
    return score


def _normalize_title(title: str) -> str:
    """Normalize title for comparison (lowercase, no punctuation/spaces)."""
    normalized = title.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", "", normalized).strip()
    return normalized


def _get_title_tokens(title: str) -> set[str]:
    """Extract significant tokens from title (length > 2)."""
    cleaned = re.sub(r"[^\w\s]", " ", title.lower())
    return {token for token in cleaned.split() if len(token) > 2}


def _normalize_doi(doi: str) -> str:
    """Normalize DOI for comparison."""
    normalized = _DOI_PREFIX_PATTERN.sub("", doi.strip()).lower()
    return normalized.rstrip("/.")


# Nested reference parsing is temporarily disabled.
# Keep this helper commented to re-enable recursive resolution later.
# def _parse_nested_references(raw_nested: list) -> list[InheritedReference]:
#     """Parse nested references from LLM response."""
#     nested_refs: list[InheritedReference] = []
#
#     for item in raw_nested:
#         if not isinstance(item, dict):
#             continue
#
#         context = (item.get("nested_context_phrase") or "").strip()
#         doi = (item.get("target_doi") or "").strip() or None
#         title = (item.get("target_title") or "").strip() or None
#         raw_target_year = item.get("target_year")
#         target_year = raw_target_year if isinstance(raw_target_year, int) else None
#
#         # Require context and at least one identifier
#         if context and (doi or title):
#             nested_refs.append(
#                 InheritedReference(
#                     context_phrase=context,
#                     target_doi=doi,
#                     target_title=title,
#                     target_year=target_year,
#                 )
#             )
#
#     return nested_refs


if __name__ == "__main__":
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
        
        # Adjust concurrency based on your system and API rate limits
        resolver = ReferenceResolver(
            max_concurrent_protocols=10,  # Process 10 protocols in parallel
            max_concurrent_fetches=5,     # 5 concurrent paper fetches per protocol
        )
        
        resolved = await resolver.resolve_all(protocols)
        save_json(resolved, STEP8_FILE)
        print(
            f"Processed {len(resolved)} protocols with score >= 70 for reference resolution."
        )
        print(
            f"[Step 8] DONE | input={len(protocols)} output={len(resolved)} | "
            f"Output: intermediate_outputs/{STEP8_FILE}"
        )

    asyncio.run(_main())