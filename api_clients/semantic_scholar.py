"""Semantic Scholar API client.

Docs: https://api.semanticscholar.org/api-docs/
"""
from __future__ import annotations

import logging
from typing import List, Optional

from config import get_settings
from models.paper import Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
_FIELDS = "paperId,externalIds,title,abstract,year,authors,openAccessPdf"


class SemanticScholarClient(BaseAPIClient):
    """Wrapper around the Semantic Scholar Graph API."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if _settings.semantic_scholar_api_key:
            headers["x-api-key"] = _settings.semantic_scholar_api_key
        return headers

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": _FIELDS,
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("SemanticScholar search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("data", []):
            doi = (item.get("externalIds") or {}).get("DOI")
            papers.append(
                Paper(
                    doi=doi,
                    title=item.get("title", "Untitled"),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    abstract=item.get("abstract"),
                    year=item.get("year"),
                    source="semantic_scholar",
                    url=(item.get("openAccessPdf") or {}).get("url"),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[str]:
        """For Semantic Scholar we rely on the open-access PDF URL stored in paper.url."""
        if not paper.url:
            return None
        try:
            resp = await self._get(paper.url)
            # Return raw bytes as text (caller will handle PDF extraction if needed)
            return resp.text
        except Exception as exc:  # noqa: BLE001
            logger.warning("SemanticScholar full-text fetch failed: %s", exc)
            return None
