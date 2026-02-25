"""Module 4 – Recursive Protocol Extractor ("Citation Investigator").

Uses Gemini to:
1. Parse a paper's full text and return structured protocol steps.
2. If a step references another paper (e.g. "[14]"), resolve that reference,
   fetch its full text, and re-run extraction to fill in the details.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from api_clients.crossref import CrossRefClient
from api_clients.europe_pmc import EuropePMCClient
from api_clients.openalex import OpenAlexClient
from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from models.protocol import ExtractedProtocol, ProtocolStep
from utils.json_utils import extract_json

logger = logging.getLogger(__name__)
_s = get_settings()

# ── Prompt templates ──────────────────────────────────────────────────────────

_EXTRACT_SYSTEM = """You are a biomedical protocol extraction engine.
Given the full text of a scientific paper, extract the experimental protocol.
Output ONLY a valid JSON object matching this schema (no markdown, no preamble):

{
  "protocol_name": "<concise name for the protocol>",
  "steps": [
    {
      "step_number": 1,
      "description": "<what is done in this step>",
      "reagents": ["<reagent1>"],
      "equipment": ["<equipment1>"],
      "duration": "<optional time string>",
      "notes": "<optional notes>",
      "citation_ref": "<e.g. [14] if the step defers to another paper, else null>"
    }
  ],
  "unresolved_citations": ["[14]", "[22]"],
  "raw_bibliography": "<the full bibliography / references section as plain text>"
}

Be exhaustive with steps. Mark citation_ref when a step says something like
'as previously described [14]' or 'following the method of Smith et al. [14]'.
"""

_REFINE_SYSTEM = """You previously extracted a protocol step that deferred to an
external citation. Below is the full text of THAT cited paper.
Expand the step marked with citation_ref using the new information.
Output ONLY the updated JSON protocol (same schema, same step list).
"""


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
            data = extract_json(raw)
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
        """Resolve a DOI to a Paper with full text via CrossRef + Europe PMC."""
        paper: Optional[Paper] = None
        async with CrossRefClient() as cr:
            paper = await cr.resolve_doi(doi)

        if paper is None:
            return None

        # Attempt full-text via Europe PMC
        async with EuropePMCClient() as epmc:
            text = await epmc.fetch_full_text(paper)

        if not text:
            async with OpenAlexClient() as oa:
                oa_papers = await oa.search(f"doi:{doi}", max_results=1)
                if oa_papers:
                    paper.url = oa_papers[0].url
                    async with OpenAlexClient() as oa2:
                        text = await oa2.fetch_full_text(paper)

        if text:
            paper.full_text = FullText(
                format=FullTextFormat.XML if text.lstrip().startswith("<") else FullTextFormat.PLAIN,
                content=text,
            )
        return paper

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
