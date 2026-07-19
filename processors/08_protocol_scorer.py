"""Re-score extracted protocols before final formatting.

Reads protocols after recursive extraction and updates their
``relevance_score`` using an LLM pass focused on protocol executability,
completeness, and alignment with user intent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time as _time
from typing import Any, Optional

import httpx

from config import get_settings
from models.protocol import ExtractedProtocol, ScoringOutput
from utils.llm_client import BaseLLMProcessor

logger = logging.getLogger(__name__)
_s = get_settings()

_SCORER_SYSTEM = """You are a biomedical protocol evaluator.
Given the user intent and a resolved protocol text, assign a relevance score from 0 to 100.

## Your task
- Read the user intent and the resolved protocol text.
1. Read the user intent.
2. Read the combined protocol text, treating [Level 0] as the core focus and [Level 1] as supplementary technical support.
3. Assess how well the *synthesized* information (Level 0 + Level 1) meets the user's needs and how complete it is for practical, bench-side execution.
4. Assign a final relevance score from 0 to 100 based on the scoring ccriteria.
5. Provide a brief scoring justification (max 30 words) explaining the main reason for the assigned score.

## Scoring criteria
- Intent Alignment / Relevance (Weight: 50%): Does the primary protocol ([Level 0]) directly address the user's specific technique, biological target, or research intent, without mixing in steps from an unrelated technique or procedure? This is the single most important criterion — a strong mismatch here should cap the overall score low even if other criteria score well.
- Operational Completeness (Weight: 25%): Are all steps, reagents, equipment, and measurable parameters (concentrations, timings, temperatures, volumes) expected for this technique present across the combined levels?
  * IMPORTANT: If [Level 0] lacks detail, check if [Level 1] successfully provides the missing steps.
  * Penalize the score if crucial steps are still missing across all levels.
- Parameter Plausibility (Weight: 15%): Are the numerical values and conditions present (times, temperatures, concentrations, volumes, units) internally consistent and physicochemically plausible, without contradictions between [Level 0] and [Level 1]?
- Executability (Weight: 10%): Given the content present, are the instructions explicit and unambiguous enough that a researcher could act on them without needing to guess or infer unstated details?

## Input
The input text you will evaluate contains a main protocol and its supporting nested protocols, labeled by their hierarchical relationship:
- [Level 0]: The primary protocol extracted from the main source document.
- [Level 1]: Nested or cited protocols (e.g., extracted because [Level 0] referenced them via phrases like "prepared as described previously"). These provide the missing operational details for [Level 0].
"""

_SCORER_SCHEMA: dict = {
    "name": "rescored_protocol",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "relevance_score": {"type": "number"},
            "scoring_justification": {"type": "string"},
        },
        "required": ["relevance_score", "scoring_justification"],
        "additionalProperties": False,
    },
}


class ProtocolScorer(BaseLLMProcessor):
    """Re-score protocols after recursive extraction."""

    def __init__(self, max_concurrent_scores: int = _s.llm_max_concurrent) -> None:
        super().__init__("8")
        self._score_semaphore = asyncio.Semaphore(max_concurrent_scores)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def score_all(
        self,
        protocols: list[ExtractedProtocol],
        user_intent: str,
    ) -> list[ExtractedProtocol]:
        """Re-score all input protocols and return the updated list."""
        self._llm_token_events.clear()
        self._llm_call_count = 0
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

        return rescored

    async def _score_one_with_semaphore(
        self,
        protocol: ExtractedProtocol,
        user_intent: str,
    ) -> ExtractedProtocol:
        async with self._score_semaphore:
            return await self._score_one(protocol, user_intent)

    async def _score_one(
        self, protocol: ExtractedProtocol, user_intent: str
    ) -> ExtractedProtocol:
        scoring_text = self._build_scoring_text(protocol)
        if not scoring_text:
            protocol.relevance_score = 0.0
            protocol.scoring_justification = (
                "No protocol content at levels 0-1 available for LLM scoring."
            )
            return protocol

        user_prompt = (
            f"User intent:\n{user_intent}\n\n"
            "Resolved protocol text (levels 0 and 1 only):\n"
            f"{scoring_text[:120_000]}"
        )
        payload: dict[str, Any] = {
            "model": _s.llm_model_general,
            "messages": [
                {"role": "system", "content": _SCORER_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_schema", "json_schema": _SCORER_SCHEMA},
        }

        try:
            _t0 = _time.monotonic()
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
            _gen_ms = (_time.monotonic() - _t0) * 1000

            if resp.is_error:
                logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                resp.raise_for_status()
            raw_payload = resp.json()
            self._record_llm_usage(raw_payload, generation_time_ms=_gen_ms)
            data = self._extract_json_content(raw_payload)
            scoring = ScoringOutput.model_validate(data)

            protocol.relevance_score = max(0.0, min(100.0, scoring.relevance_score))
            protocol.scoring_justification = (
                scoring.scoring_justification[:300]
                if scoring.scoring_justification.strip()
                else "No justification returned by scorer model."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Protocol re-scoring failed for '%s': %s",
                protocol.source_title[:100],
                exc,
            )
            if not protocol.scoring_justification:
                protocol.scoring_justification = (
                    "Scoring call failed; retained previous relevance score."
                )

        return protocol

    def _extract_json_content(self, response_json: dict[str, Any]) -> dict[str, Any]:
        content = (
            response_json.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "{}")
        )

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        if not isinstance(content, str):
            content = str(content)

        return json.loads(content)

    def _build_scoring_text(self, protocol: ExtractedProtocol) -> str:
        """Build scoring text using only local recursion levels 0 and 1."""
        blocks: list[str] = []
        queue: list[tuple[ExtractedProtocol, int]] = [(protocol, 0)]

        while queue:
            current, local_level = queue.pop(0)
            if local_level > 1:
                continue

            text = (current.protocol_text or "").strip()
            if text:
                blocks.append(f"[Level {local_level}] {current.source_title}\n{text}")

            if local_level < 1 and current.nested_protocols:
                queue.extend(
                    (child, local_level + 1) for child in current.nested_protocols
                )

        return "\n\n".join(blocks).strip()


if __name__ == "__main__":
    import asyncio
    from utils.logger import set_stage_logger, setup_logging

    setup_logging()
    set_stage_logger("step8_protocol_scoring")

    from config import get_settings
    from utils.telemetry import log_standalone_telemetry

    from models.query import ExpandedQuery
    from utils.intermediate_io import (
        STEP1_FILE,
        STEP7_FILE,
        STEP8_FILE,
        load_model,
        load_model_list,
        save_json,
    )

    async def _main() -> None:
        logger.info("[Step 8] START | Protocol Scoring")
        intent = load_model(STEP1_FILE, ExpandedQuery).intent
        protocols = load_model_list(STEP7_FILE, ExtractedProtocol)
        scorer = ProtocolScorer()
        rescored = await scorer.score_all(protocols, intent)
        save_json(rescored, STEP8_FILE)
        logger.info("Re-scored %d protocols from Step 7 output.", len(rescored))
        logger.info(
            "[Step 8] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
            len(protocols),
            len(rescored),
            STEP8_FILE,
        )

        events = scorer.get_llm_token_events()
        _s = get_settings()
        await log_standalone_telemetry(events, _s.llm_model_general, "protocol_scorer")

    asyncio.run(_main())
