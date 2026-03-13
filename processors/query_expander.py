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

_SYSTEM_PROMPT = _SYSTEM_PROMPT = """You are an expert academic search architect specializing in multi-database query optimization.  

## Your job
Given a description of an experimental technique or research need, generate optimized search queries to retrieve relevant scientific papers.

## Query construction rules

### structured_boolean (Europe PMC, Scopus, PubMed)
- Use AND between layers, OR within each layer for synonyms and related terms
- Use field tags [title] or [abstract] on the most specific terms
- Generate queries ranging from broad (1–2 layers) to narrow (3–4 layers)
- Include MeSH terms where applicable, paired with free-text synonyms

### concept_strings (OpenAlex, CrossRef, Semantic Scholar)
- 2–5 terms per string, no operators, no full sentences
- Include synonyms and established abbreviations as separate strings

## Output rules
- Generate 3–5 queries per category, varying from broad to narrow in specificity.
- Vary synonyms and adjacent concepts across strings
- Do not repeat the same phrase across more than 3 queries in a category
- Every term must belong to the biological domain of the user's question
- Prioritize specificity: a narrow query that returns 50 highly relevant papers is better than a broad one returning 5000 mixed results

## What NOT to include in queries
- Do not add methodological terms (e.g., "protocol", "assay", "sequencing")
- Do not add study-type terms (e.g., "study", "analysis", "investigation", "research", "review") — these are noise, not signal
- Do not add generic scientific verbs (e.g., "role of", "effect of", "impact of") unless they are part of an established technical term
"""

_EXPANDED_QUERY_SCHEMA:dict = {
    "name": "expanded_query",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "description": "One-sentence summary of the user's research intent.",
            },
            "structured_boolean": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Queries optimized for Europe PMC/Scopus (e.g., '(term1 OR term2) AND method[title]')",
            },
            "concept_strings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Clean keyword strings for OpenAlex/Crossref/Unpaywall.",
            },
        },
        "required": ["intent", "structured_boolean", "concept_strings"],
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
        print(f"structured_boolean: {expanded.structured_boolean}")
        print(f"concept_strings: {expanded.concept_strings}")
        print(f"\nSaved → intermediate_outputs/{STEP1_FILE}")

    asyncio.run(_main())
