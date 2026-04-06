"""Protocol extraction step (no recursive resolution).

This step extracts protocol fragments from each paper and returns JSON-ready
objects with protocol_text, relevance_score, and inherited_references.

Only payloads with relevance_score == 0.0 and empty protocol_text are discarded.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

from config import get_settings
from models.paper import Paper
from models.protocol import ExtractedProtocol, InheritedReference

logger = logging.getLogger(__name__)
_s = get_settings()

_EXTRACT_SYSTEM = """You are a biomedical protocol extraction engine.
Given the user intent and the full text of a scientific paper, extract the experimental protocol.

### EXTRACTION RULES
1.  **Intent filtering:** If the paper does not contain a protocol matching the user intent, return an empty `protocol_text` and a `relevance_score` of 0.
2.  **Verbatim extraction:** Extract `protocol_text` as plain text.
    - Do not sacrifice completeness for brevity. Include the full logical sequence: from initial preparation (buffers, reagents, concentrations, cell lines) to the final measurement/analysis.
    - Preserve original technical terminology. If a step mentions specific temperatures, incubation times, or specialized equipment, it MUST be included.
    - If the protocol is distributed across different sections (e.g., Methods, Results, and Supplementary captions), join them into a cohesive block while maintaining the original terminology.
3.  **Inherited references:** Return an `inherited_references` list with `context_phrase` and `target_doi` for inherited methods.
    -   **Context Phrase:** Must be the specific anchor text used in the paper (e.g., "following the method of Smith et al.").
    -   **Target DOI:** Extract the DOI if present; otherwise, provide the citation string.
4.  **Scoring:** Assign a `relevance_score` from 0 to 100 based on how well the protocol matches the user intent, where 100 is a perfect match. Consider relevance, completeness, and specificity.

### INHERITANCE RULES
Include an inherited reference ONLY when the missing detail is indispensable for execution or reproducibility
AND that detail is not already described in the current paper.
If uncertain, prefer an empty `inherited_references` list.

Examples of when to include inherited references:
-   If the protocol says "We performed RNA-seq as described in Smith et al.," include an inherited reference to Smith et al.
-   If the protocol says "Cell viability was measured using a previously established assay," include an inherited reference to the cited method.
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
                        "target_doi": {"type": "string"},
                    },
                    "required": ["context_phrase", "target_doi"],
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

    def __init__(self) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

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

        inherited = [
            InheritedReference(
                context_phrase=ref["context_phrase"].strip(),
                target_doi=ref["target_doi"].strip(),
            )
            for ref in payload.get("inherited_references", [])
            if ref.get("context_phrase") and ref.get("target_doi")
        ]

        return ExtractedProtocol(
            source_doi=paper.doi,
            source_title=paper.title,
            protocol_text=protocol_text,
            relevance_score=score,
            inherited_references=inherited,
        )

    async def _call_llm(self, text: str, user_intent: str) -> Optional[Dict[str, Any]]:
        prompt = f"User intent:\n{user_intent}\n\nPaper text:\n{text}"
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
        protocols: list[ExtractedProtocol] = []
        logger.info("Step 7 start - Protocol extraction on %d papers.", len(papers))
        for paper in papers:
            proto = await extractor.extract(paper, intent)
            if proto:
                protocols.append(proto)
        logger.info(
            "Step 7 complete - Extracted %d protocols from %d eligible papers.",
            len(protocols),
            len(papers),
        )
        save_json(protocols, STEP7_FILE)
        print(f"Extracted {len(protocols)} protocols.")
        print(
            f"[Step 7] DONE | input={len(papers)} output={len(protocols)} | Output: intermediate_outputs/{STEP7_FILE}"
        )

    asyncio.run(_main())
