"""Module 1 – Query Expansion.

Uses Gemini 1.5 Flash (via OpenRouter) to transform the raw user prompt
into structured keyword and semantic queries.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config import get_settings
from models.query import ExpandedQuery

logger = logging.getLogger(__name__)
_s = get_settings()

_SYSTEM_PROMPT = """You are an expert biomedical literature search assistant.
Given a user's natural language research intent, expand it into structured search queries.

Rules:
- keyword_queries: 3-5 entries using MeSH terms, Boolean operators (AND/OR/NOT),
  and field tags where appropriate (e.g. [ti], [ab]).
- semantic_queries: 2-4 entries as full natural-language sentences describing
  the biological method, protocol, or technique sought.
"""

_EXPANDED_QUERY_SCHEMA: dict = {
    "name": "expanded_query",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "One-sentence summary of the user's research intent.",
            },
            "keyword_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "3-5 Boolean/keyword search strings using MeSH terms and field tags.",
            },
            "semantic_queries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-4 natural-language sentences for semantic/vector search.",
            },
        },
        "required": ["intent", "keyword_queries", "semantic_queries"],
        "additionalProperties": False,
    },
}


class QueryExpander:
    """Calls Gemini via OpenRouter and returns a validated :class:`ExpandedQuery`."""

    def __init__(self) -> None:
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }

    async def expand(self, user_prompt: str) -> ExpandedQuery:
        payload: dict[str, Any] = {
            "model": _s.gemini_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_schema", "json_schema": _EXPANDED_QUERY_SCHEMA},
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

        raw_content: str = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(raw_content)
        return ExpandedQuery(**data)


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import STEP1_FILE, save_json  # noqa: E402

    if len(sys.argv) < 2:
        print('Usage: python processors/query_expander.py "<your research question>"')
        sys.exit(1)

    _prompt = " ".join(sys.argv[1:])

    async def _main() -> None:
        expander = QueryExpander()
        expanded = await expander.expand(_prompt)
        save_json(expanded, STEP1_FILE)
        print(f"Intent  : {expanded.intent}")
        print(f"Keywords: {expanded.keyword_queries}")
        print(f"Semantic: {expanded.semantic_queries}")
        print(f"\nSaved → intermediate_outputs/{STEP1_FILE}")

    asyncio.run(_main())
