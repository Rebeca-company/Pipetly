"""Protocol extraction step (no recursive resolution).

This step extracts protocol fragments from each paper and returns JSON-ready
objects with protocol_text, relevance_score, and inherited_references.

Only payloads with relevance_score == 0.0 and empty protocol_text are discarded.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import httpx

from config import get_settings
from models.paper import Paper
from models.protocol import ExtractedProtocol, InheritedReference

logger = logging.getLogger(__name__)
_s = get_settings()

_EXTRACT_SYSTEM = """
You are a specialized biomedical protocol extraction engine. Your goal is to identify and extract laboratory procedures and the external sources necessary to replicate them.

## Your task
Extract the experimental procedure from the provided scientific paper that matches the User Intent.

## EXTRACTION RULES
1. **Intent filtering:** If the paper does not contain any protocol that matches the user intent, return an empty `protocol_text` and a `relevance_score` of 0.

2. **Verbatim sentence-level extraction:** 
    - Build `protocol_text` using the paper’s original text (no summarization).
    - Bias strongly toward including too much procedural detail rather than too little.
    - Preserve all technical values: catalogue numbers, vendors, buffer compositions, speeds, volumes, temperatures, pH, wavelengths, software versions, and exclusion rules.
    - If the protocol is split across sections (Methods/Results/Figure legends/Supplementary), concatenate the paragraphs preserving their original wording.
    - Keep the original order of sentences and sections.

3. **Inherited references (Procedural Dependency):** If the protocol offloads the "how-to" of a key step to another paper, include an `inherited_references`.
    - Include in inherited_references **ONLY** if the cited source has to be consulted to physically replicate a laboratory action (e.g., "prepared as described in...", "assayed following...").
    - Prefer an empty list rather than including inherited references unnecessary to protocol execution.
    - `context_phrase`: Use the exact anchor text (e.g., "purified by the method proposed by...", "following the procedure modified from...").
    - Metadata: Extract `target_doi`, or if unavailable, `target_title` and `target_year`.
    - EXCLUSION CRITERIA:
        - NO Clinical/Biological Context: Exclude citations used to justify the study, explain disease mechanisms, or provide reference ranges (e.g., "Normal LDH levels are 10-20% [5]").
        - NO Background Findings: Exclude citations of previous results or applications (e.g., "Smith et al. used this to detect pregnancy [8]").
        - NO Software/Statistics: Exclude ImageJ, GraphPad, ANOVA, or database citations (e.g., UniProt, STRING).
        - NO General Equipment/Materials: Exclude citations that only identify a commercial kit or reagent unless the text says the *method* was followed from that specific paper.

5. **Scoring:** Assign `relevance_score` (0-100) based on how well the extracted protocol allows for physical replication of the user intent.
"""

_EXTRACTED_PROTOCOL_SCHEMA: dict = {
    "name": "protocol_fragment_payload",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "protocol_text": {"type": "string"},
            "relevance_score": {"type": "number"},
            "inherited_references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "context_phrase": {"type": "string"},
                        "target_doi": {"type": ["string", "null"]},
                        "target_title": {"type": ["string", "null"]},
                        "target_year": {"type": ["integer", "null"]},
                    },
                    "required": ["context_phrase"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["protocol_text", "relevance_score", "inherited_references"],
        "additionalProperties": False,
    },
}


class ProtocolExtractor:
    """Extract protocol fragments and inherited references from one paper."""

    def __init__(self, max_concurrent_extractions: int = _s.llm_max_concurrent) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }
        self._extract_semaphore = asyncio.Semaphore(max_concurrent_extractions)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def extract_all(
        self,
        papers: list[Paper],
        user_intent: str,
    ) -> list[ExtractedProtocol]:
        """Extract protocols from papers concurrently with bounded fan-out."""
        logger.info("Step 7 start - Protocol extraction on %d papers.", len(papers))
        self._http_client = httpx.AsyncClient(
            timeout=_s.http_timeout * 2,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        try:
            tasks = [
                self._extract_with_semaphore(paper, user_intent)
                for paper in papers
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await self._http_client.aclose()
            self._http_client = None

        protocols: list[ExtractedProtocol] = []
        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Protocol extraction failed for '%s': %s",
                    paper.title[:100],
                    result,
                )
                continue
            if result is not None:
                protocols.append(result)

        logger.info(
            "Step 7 complete - Extracted %d protocols from %d eligible papers.",
            len(protocols),
            len(papers),
        )
        return protocols

    async def _extract_with_semaphore(
        self,
        paper: Paper,
        user_intent: str,
    ) -> Optional[ExtractedProtocol]:
        async with self._extract_semaphore:
            return await self.extract(paper, user_intent)

    async def extract(self, paper: Paper, user_intent: str) -> Optional[ExtractedProtocol]:
        """Extract protocol payload and discard only empty + zero-score entries."""
        if not paper.full_text or not paper.full_text.content.strip():
            return None

        payload = await self._call_llm(paper.full_text.content, user_intent)
        if payload is None:
            return None

        score = float(payload.get("relevance_score", 0.0))
        protocol_text = payload.get("protocol_text", "").strip()

        # Step 7 keeps low-score candidates; only discard clear non-matches.
        if score == 0.0 and not protocol_text:
            return None

        inherited: list[InheritedReference] = []
        for ref in payload.get("inherited_references", []):
            context_phrase = (ref.get("context_phrase") or "").strip()
            target_doi = (ref.get("target_doi") or "").strip() or None
            target_title = (ref.get("target_title") or "").strip() or None
            raw_target_year = ref.get("target_year")
            target_year = raw_target_year if isinstance(raw_target_year, int) else None

            if not context_phrase:
                continue

            # Keep only resolvable references.
            if not (target_doi or target_title):
                continue

            inherited.append(
                InheritedReference(
                    context_phrase=context_phrase,
                    target_doi=target_doi,
                    target_title=target_title,
                    target_year=target_year,
                )
            )

        return ExtractedProtocol(
            source_doi=paper.doi,
            source_title=paper.title,
            protocol_text=protocol_text,
            relevance_score=score,
            inherited_references=inherited,
        )

    async def _call_llm(self, text: str, user_intent: str) -> Optional[Dict[str, Any]]:
        prompt = (
            "User intent:\n"
            f"{user_intent}\n\n"
            "Paper text:\n"
            f"{text}"
        )
        req: dict[str, Any] = {
            "model": _s.gemini_model_fulltext,
            "messages": [
                {"role": "system", "content": _EXTRACT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _EXTRACTED_PROTOCOL_SCHEMA},
        }
        try:
            if self._http_client is not None:
                resp = await self._http_client.post(
                    f"{self._base}/chat/completions",
                    json=req,
                    headers=self._headers,
                )
            else:
                async with httpx.AsyncClient(timeout=_s.http_timeout * 2) as client:
                    resp = await client.post(
                        f"{self._base}/chat/completions",
                        json=req,
                        headers=self._headers,
                    )

            if resp.is_error:
                logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.error("Protocol extraction failed: %s", exc)
            return None

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    from models.query import ExpandedQuery
    from utils.intermediate_io import (
        STEP1_FILE,
        STEP6_FILE,
        STEP7_FILE,
        load_model,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        print("[Step 7] START | Protocol Extraction")
        papers = load_model_list(STEP6_FILE, Paper)
        intent = load_model(STEP1_FILE, ExpandedQuery).intent
        extractor = ProtocolExtractor()
        protocols = await extractor.extract_all(papers, intent)
        save_json(protocols, STEP7_FILE)
        print(f"Extracted {len(protocols)} protocols.")
        print(
            f"[Step 7] DONE | input={len(papers)} output={len(protocols)} | Output: intermediate_outputs/{STEP7_FILE}"
        )

    asyncio.run(_main())
