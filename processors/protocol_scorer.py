"""Re-score resolved protocols before final formatting.

Reads protocols after inherited-reference resolution and updates their
``relevance_score`` using an LLM pass focused on protocol executability,
completeness, and alignment with user intent.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import httpx

from config import get_settings
from models.protocol import ExtractedProtocol

logger = logging.getLogger(__name__)
_s = get_settings()

_SCORER_SYSTEM = """You are a biomedical protocol evaluator.
Given the user intent and a resolved protocol text, assign a relevance score from 0 to 100.

Scoring criteria:
- Intent alignment (does it solve what the user asked? meet the research topic or technique of interest?)
- Operational completeness (materials, conditions, timings, and steps)

Rules:
- Be strict and evidence-based.
- Do not reward generic or incomplete protocols.
"""

_SCORER_SCHEMA: dict = {
    "name": "rescored_protocol",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "relevance_score": {"type": "number"}
        },
        "required": ["relevance_score"],
        "additionalProperties": False,
    },
}


class ProtocolScorer:
    """Re-score protocols after inherited-reference resolution."""

    def __init__(self, max_concurrent_scores: int = _s.llm_max_concurrent) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }
        self._score_semaphore = asyncio.Semaphore(max_concurrent_scores)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def score_all(
        self,
        protocols: list[ExtractedProtocol],
        user_intent: str,
    ) -> list[ExtractedProtocol]:
        """Re-score all input protocols and return the updated list."""
        logger.info("Step 9 start - Re-scoring %d protocols.", len(protocols))
        self._http_client = httpx.AsyncClient(
            timeout=_s.http_timeout * 2,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

        try:
            tasks = [
                self._score_one_with_semaphore(protocol, user_intent)
                for protocol in protocols
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await self._http_client.aclose()
            self._http_client = None

        rescored: list[ExtractedProtocol] = []
        for protocol, result in zip(protocols, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Protocol re-scoring failed for '%s': %s",
                    protocol.source_title[:100],
                    result,
                )
                rescored.append(protocol)
                continue
            rescored.append(result)

        logger.info("Step 9 complete - Re-scored %d protocols.", len(rescored))
        return rescored

    async def _score_one_with_semaphore(
        self,
        protocol: ExtractedProtocol,
        user_intent: str,
    ) -> ExtractedProtocol:
        async with self._score_semaphore:
            return await self._score_one(protocol, user_intent)

    async def _score_one(self, protocol: ExtractedProtocol, user_intent: str) -> ExtractedProtocol:
        if not protocol.protocol_text.strip():
            protocol.relevance_score = 0.0
            return protocol

        user_prompt = (
            f"User intent:\n{user_intent}\n\n"
            "Resolved protocol text:\n"
            f"{protocol.protocol_text[:120_000]}"
        )
        payload: dict[str, Any] = {
            "model": _s.gemini_model_general,
            "messages": [
                {"role": "system", "content": _SCORER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _SCORER_SCHEMA},
        }

        try:
            if self._http_client is not None:
                resp = await self._http_client.post(
                    f"{self._base}/chat/completions",
                    json=payload,
                    headers=self._headers,
                )
            else:
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
            score = float(data.get("relevance_score", protocol.relevance_score))
            protocol.relevance_score = max(0.0, min(100.0, score))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Protocol re-scoring failed for '%s': %s",
                protocol.source_title[:100],
                exc,
            )

        return protocol


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
        STEP8_FILE,
        STEP9_FILE,
        load_model,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        print("[Step 9] START | Protocol Scoring")
        intent = load_model(STEP1_FILE, ExpandedQuery).intent
        protocols = load_model_list(STEP8_FILE, ExtractedProtocol)
        rescored = await ProtocolScorer().score_all(protocols, intent)
        save_json(rescored, STEP9_FILE)
        print(f"Re-scored {len(rescored)} protocols from Step 8 output.")
        print(
            f"[Step 9] DONE | input={len(protocols)} output={len(rescored)} | Output: intermediate_outputs/{STEP9_FILE}"
        )

    asyncio.run(_main())
