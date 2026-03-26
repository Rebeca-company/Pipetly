"""Module 4 – Recursive Protocol Extractor ("Citation Investigator").

Uses Gemini to:
1. Parse a paper's full text and return structured protocol steps.
2. If a step references another paper (e.g. "[14]"), resolve that reference,
   fetch its full text, and re-run extraction to fill in the details.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from api_clients.europe_pmc import EuropePMCClient
from api_clients.semantic_scholar import SemanticScholarClient
from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from models.protocol import ExtractedProtocol, ProtocolStep

logger = logging.getLogger(__name__)
_s = get_settings()

# ── Prompt templates ──────────────────────────────────────────────────────────

_EXTRACT_SYSTEM = """You are a biomedical protocol extraction engine.
Given the full text of a scientific paper, extract the experimental protocol exhaustively.
Mark citation_ref on any step that defers to another paper
(e.g. 'as previously described [14]') using the bracket notation, e.g. '[14]'.
Include the full bibliography/references section verbatim in raw_bibliography.
"""

_REFINE_SYSTEM = """You previously extracted a protocol step that deferred to an
external citation. Below is the full text of THAT cited paper.
Expand the step marked with citation_ref using the new information.
Return the updated protocol using the same schema.
"""

_STEP_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "step_number": {"type": "integer"},
        "description": {"type": "string", "description": "What is done in this step."},
        "reagents": {"type": "array", "items": {"type": "string"}},
        "equipment": {"type": "array", "items": {"type": "string"}},
        "duration": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Optional time string for the step.",
        },
        "notes": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Optional additional notes.",
        },
        "citation_ref": {
            "anyOf": [{"type": "string"}, {"type": "null"}],
            "description": "Bracket citation if the step defers to another paper, e.g. '[14]'.",
        },
    },
    "required": ["step_number", "description", "reagents", "equipment", "duration", "notes", "citation_ref"],
    "additionalProperties": False,
}

_EXTRACTED_PROTOCOL_SCHEMA: dict = {
    "name": "extracted_protocol",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "protocol_name": {
                "type": "string",
                "description": "Concise name for the extracted protocol.",
            },
            "steps": {
                "type": "array",
                "items": _STEP_SCHEMA,
                "description": "Exhaustive ordered list of protocol steps.",
            },
            "unresolved_citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Citation markers that require external resolution.",
            },
            "raw_bibliography": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "description": "Full references section as plain text.",
            },
        },
        "required": ["protocol_name", "steps", "unresolved_citations", "raw_bibliography"],
        "additionalProperties": False,
    },
}


# ── Citation key → DOI resolver ───────────────────────────────────────────────

_CITATION_KEY_RE = re.compile(r"\[(\d+)\]")


def _parse_doi_from_bibliography(raw_bib: str, citation_key: str) -> Optional[str]:
    """
    Heuristic: scan the bibliography text for a line starting with the
    citation number and extract the first DOI-like string.
    """
    key_num = citation_key.strip("[]")
    doi_re = re.compile(r"10\.\d{4,9}/\S+", re.IGNORECASE)
    for line in raw_bib.splitlines():
        if re.match(rf"^\s*\[?{re.escape(key_num)}\]?\s*\.?\s+", line):
            m = doi_re.search(line)
            if m:
                return m.group(0).rstrip(".,;)")
    # Fallback: search for DOI anywhere near the key
    snippet_start = raw_bib.find(f"[{key_num}]")
    if snippet_start != -1:
        snippet = raw_bib[snippet_start: snippet_start + 400]
        m = doi_re.search(snippet)
        if m:
            return m.group(0).rstrip(".,;)")
    return None


# ── Main extractor class ──────────────────────────────────────────────────────


class ProtocolExtractor:
    def __init__(self) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

    # ── Public API ────────────────────────────────────────────────────────────

    async def extract(self, paper: Paper) -> Optional[ExtractedProtocol]:
        """Extract protocol from *paper*, recursively resolving citations."""
        if not paper.full_text:
            return None
        text = _clean_text(paper.full_text.content)
        protocol = await self._call_gemini(text, _EXTRACT_SYSTEM)
        if protocol is None:
            return None

        # Recursive citation investigation
        await self._investigate_citations(protocol, depth=0)

        protocol.source_doi = paper.doi
        protocol.source_title = paper.title
        return protocol

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _call_gemini(
        self, text: str, system_prompt: str
    ) -> Optional[ExtractedProtocol]:
        payload: dict[str, Any] = {
            "model": _s.gemini_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text[:120_000]},  # stay within context
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _EXTRACTED_PROTOCOL_SCHEMA},
        }
        try:
            async with httpx.AsyncClient(timeout=_s.http_timeout * 2) as client:
                resp = await client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
                if resp.is_error:
                    logger.error(
                        "OpenRouter error %s – %s", resp.status_code, resp.text
                    )
                    resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(raw)
            return _parse_protocol(data)
        except Exception as exc:  # noqa: BLE001
            logger.error("Gemini extraction failed: %s", exc)
            return None

    async def _investigate_citations(
        self, protocol: ExtractedProtocol, depth: int
    ) -> None:
        """Recursively resolve unresolved citation refs up to max depth."""
        if depth >= _s.max_citation_depth:
            return
        if not protocol.unresolved_citations or not protocol.raw_bibliography:
            return

        for citation_key in list(protocol.unresolved_citations):
            doi = _parse_doi_from_bibliography(protocol.raw_bibliography, citation_key)
            if not doi:
                logger.debug("Could not resolve DOI for citation %s", citation_key)
                continue

            cited_paper = await self._fetch_cited_paper(doi)
            if cited_paper is None or cited_paper.full_text is None:
                continue

            logger.info(
                "Citation Investigator [depth=%d]: resolving %s → %s",
                depth,
                citation_key,
                doi,
            )
            # Re-run extraction on cited paper to get its protocol
            cited_text = _clean_text(cited_paper.full_text.content)
            cited_protocol = await self._call_gemini(cited_text, _EXTRACT_SYSTEM)
            if cited_protocol is None:
                continue

            # Merge: replace stub steps referencing this citation with cited steps
            self._merge_cited_steps(protocol, citation_key, cited_protocol)

            # Recurse into the cited paper's citations
            if cited_protocol.unresolved_citations and cited_protocol.raw_bibliography:
                await self._investigate_citations(cited_protocol, depth + 1)

            protocol.unresolved_citations.remove(citation_key)

    async def _fetch_cited_paper(self, doi: str) -> Optional[Paper]:
        """Resolve a DOI to a Paper with full text via Europe PMC or Semantic Scholar."""
        # Try to fetch full text by DOI using Europe PMC first
        paper = Paper(
            doi=doi,
            title="Cited paper",
            authors=[],
            abstract=None,
            year=None,
            source="citation_investigation",
        )

        # Primary: Europe PMC (has XML full-text for PMC articles)
        async with EuropePMCClient() as epmc:
            text = await epmc.fetch_full_text(paper)
            if text:
                paper.full_text = text
                return paper

        # Fallback: Semantic Scholar (PDF access via DOI)
        async with SemanticScholarClient() as s2:
            text = await s2.fetch_full_text(paper)
            if text:
                paper.full_text = text
                return paper

        logger.debug("Could not fetch full text for cited DOI: %s", doi)
        return None

    @staticmethod
    def _merge_cited_steps(
        protocol: ExtractedProtocol,
        citation_key: str,
        cited_protocol: ExtractedProtocol,
    ) -> None:
        """
        Replace steps that carry *citation_key* with expanded detail from
        *cited_protocol*.
        """
        expanded_steps: list[ProtocolStep] = []
        for step in protocol.steps:
            if step.citation_ref == citation_key:
                # Inject cited steps in place of the stub
                for i, cited_step in enumerate(cited_protocol.steps):
                    expanded_steps.append(
                        cited_step.model_copy(
                            update={
                                "step_number": step.step_number + i,
                                "notes": (
                                    f"[Expanded from citation {citation_key}] "
                                    + (cited_step.notes or "")
                                ).strip(),
                                "citation_ref": None,
                            }
                        )
                    )
            else:
                expanded_steps.append(step)

        # Renumber steps sequentially
        for idx, s in enumerate(expanded_steps, start=1):
            s.step_number = idx
        protocol.steps = expanded_steps


# ── Helpers ───────────────────────────────────────────────────────────────────


def _clean_text(text: str) -> str:
    """Remove XML tags from XML/HTML full-text for LLM consumption."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s{2,}", " ", clean)
    return clean.strip()


def _parse_protocol(data: Dict[str, Any]) -> ExtractedProtocol:
    steps = [
        ProtocolStep(
            step_number=s.get("step_number", i + 1),
            description=s.get("description", ""),
            reagents=s.get("reagents") or [],
            equipment=s.get("equipment") or [],
            duration=s.get("duration"),
            notes=s.get("notes"),
            citation_ref=s.get("citation_ref"),
        )
        for i, s in enumerate(data.get("steps", []))
    ]
    return ExtractedProtocol(
        source_title="",  # filled in by caller
        protocol_name=data.get("protocol_name", "Unknown Protocol"),
        steps=steps,
        unresolved_citations=data.get("unresolved_citations") or [],
        raw_bibliography=data.get("raw_bibliography"),
    )


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import (  # noqa: E402
        STEP5_FILE,
        STEP7_FILE,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        papers = load_model_list(STEP5_FILE, Paper)
        extractor = ProtocolExtractor()
        protocols: list[ExtractedProtocol] = []
        for paper in papers:
            logger.info("Extracting from: %s", paper.title[:80])
            proto = await extractor.extract(paper)
            if proto:
                protocols.append(proto)
        save_json(protocols, STEP7_FILE)
        print(f"Extracted {len(protocols)} protocols.")
        print(f"Saved → intermediate_outputs/{STEP7_FILE}")

    asyncio.run(_main())
