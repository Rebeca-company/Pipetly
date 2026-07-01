"""Module 1 – Query Expansion.

Query Expansion Module (Step 1).
Uses an LLM (via OpenRouter) to transform the raw user prompt
into an expanded search intent and a list of specific keyword combinations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import get_settings
from models.query import ExpandedQuery
from utils.llm_client import BaseLLMProcessor

logger = logging.getLogger(__name__)
_s = get_settings()

_SYSTEM_PROMPT = """You are an expert academic search architect specializing in multi-database query optimization.

## Your job
Given a description of an experimental technique or research need, generate optimized search queries to retrieve relevant scientific papers.

## Intent precision rules (critical)
- The `intent` field must be a faithful, one-sentence restatement of the user's request.
- The intent must not include phrases like "Search for papers about..." or "I want to find...". It should be a direct description of the research topic or technique of interest.
- Do not add assumptions, background context, or inferred details that are not present in the user prompt.
- Do not broaden or narrow scope beyond what the user asked.
- If information is missing, keep the intent minimal rather than inventing content.
- Preserve key entities exactly when possible (targets, diseases, organisms, techniques).

## Query construction rules
- 2-5 terms per string; no operators and no full sentences.
- Include synonyms and established abbreviations as separate strings.

## Output rules
- Generate 3–5 queries, varying from broad to narrow in specificity.
- Vary synonyms and adjacent concepts across strings.
- Do not repeat the same phrase in more than 3 queries.
- Every term must belong to the biological domain of the user's question.
- Prioritize specificity: a narrow query that returns 50 highly relevant papers is better than a broad query that returns 5000 mixed results.

## What NOT to include in queries
- Do not add methodological terms (e.g., "protocol", "assay", "experiment").
- Do not add study-type terms (e.g., "study", "analysis", "investigation", "research", "review"); these are noise, not signal.
- Do not add generic scientific verbs (e.g., "role of", "effect of", "impact of") unless they are part of an established technical term.
"""

_EXPANDED_QUERY_SCHEMA: dict = {
    "name": "expanded_query",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
            },
            "queries": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["intent", "queries"],
        "additionalProperties": False,
    },
}


class QueryExpander(BaseLLMProcessor):
    """Calls the configured LLM via OpenRouter and returns a validated :class:`ExpandedQuery`."""

    def __init__(self) -> None:
        super().__init__("1")

    async def expand(self, user_prompt: str) -> ExpandedQuery:
        payload: dict[str, Any] = {
            "model": _s.llm_model_general,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {
                "type": "json_schema",
                "json_schema": _EXPANDED_QUERY_SCHEMA,
            },
        }
        async with httpx.AsyncClient(timeout=_s.http_timeout) as client:
            resp = await client.post(
                f"{self._base}/chat/completions",
                json=payload,
                headers=self._headers,
            )
            if resp.is_error:
                logger.error("OpenRouter error %s – %s", resp.status_code, resp.text)
                resp.raise_for_status()

        raw_payload = resp.json()
        self._record_llm_usage(raw_payload)
        raw_content: str = (
            raw_payload.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        )
        data = json.loads(raw_content)
        return ExpandedQuery(**data)


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import sys
    from utils.logger import set_stage_logger, setup_logging

    setup_logging()
    set_stage_logger("step1_query_expansion")

    from config import get_settings
    from utils.telemetry import log_standalone_telemetry

    from utils.intermediate_io import STEP1_FILE, save_json  # noqa: E402

    if len(sys.argv) < 2:
        print('Usage: python processors/query_expander.py "<your research question>"')
        sys.exit(1)

    _prompt = " ".join(sys.argv[1:])

    async def _main() -> None:
        logger.info("[Step 1] START | Query Expansion")
        expander = QueryExpander()
        expanded = await expander.expand(_prompt)
        save_json(expanded, STEP1_FILE)
        logger.info("Intent  : %s", expanded.intent)
        logger.info("queries: %s", expanded.queries)
        logger.info(
            "[Step 1] DONE | intent_generated=true concept_queries=%d | Output: intermediate_outputs/%s",
            len(expanded.queries),
            STEP1_FILE,
        )

        events = expander.get_llm_token_events()
        _s = get_settings()
        await log_standalone_telemetry(events, _s.llm_model_general, "query_expander")

    asyncio.run(_main())
