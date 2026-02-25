"""Module 5 – Scoring & Final Delivery.

Uses Gemini to evaluate each extracted protocol against the original search
intent and assigns a relevance score.
"""
from __future__ import annotations

import logging
from typing import Any, List

import httpx

from config import get_settings
from models.protocol import ExtractedProtocol, ScoredProtocol
from utils.json_utils import extract_json

logger = logging.getLogger(__name__)
_s = get_settings()

_SCORE_SYSTEM = """You are an expert reviewer of biomedical experimental protocols.
Given a user's research intent and an extracted protocol, evaluate how well the
protocol matches the intent.

Respond ONLY with a valid JSON object (no markdown fences):
{
  "score": <float between 0.0 and 1.0>,
  "reasoning": "<2-3 sentence explanation>"
}

Scoring rubric:
1.0 = Perfect match – the protocol directly addresses the stated intent.
0.7 = Good match – the protocol is relevant but may cover a broader technique.
0.4 = Partial match – tangentially related.
0.0 = Not relevant.
"""


class ProtocolScorer:
    """Score protocols against the original intent using Gemini."""

    def __init__(self) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

    async def score_all(
        self,
        protocols: List[ExtractedProtocol],
        intent: str,
    ) -> List[ScoredProtocol]:
        """Score every protocol and return them sorted by score (descending)."""
        import asyncio

        tasks = [self._score_one(p, intent) for p in protocols]
        scored = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[ScoredProtocol] = []
        for protocol, result in zip(protocols, scored):
            if isinstance(result, Exception):
                logger.warning("Scoring failed for '%s': %s", protocol.protocol_name, result)
                results.append(
                    ScoredProtocol(protocol=protocol, score=0.0, reasoning="Scoring failed.")
                )
            else:
                results.append(result)  # type: ignore[arg-type]

        results.sort(key=lambda sp: sp.score, reverse=True)
        return results[: _s.top_k_protocols]

    async def _score_one(
        self, protocol: ExtractedProtocol, intent: str
    ) -> ScoredProtocol:
        user_message = (
            f"Research intent:\n{intent}\n\n"
            f"Protocol name: {protocol.protocol_name}\n"
            f"Source: {protocol.source_title}\n"
            f"Steps (first 5):\n"
            + "\n".join(
                f"  {s.step_number}. {s.description}"
                for s in protocol.steps[:5]
            )
        )
        payload: dict[str, Any] = {
            "model": _s.gemini_model,
            "messages": [
                {"role": "system", "content": _SCORE_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=_s.http_timeout) as client:
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
        return ScoredProtocol(
            protocol=protocol,
            score=float(data.get("score", 0.0)),
            reasoning=data.get("reasoning", ""),
        )
