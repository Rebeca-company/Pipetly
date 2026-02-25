"""Elsevier / ScienceDirect API client.

Docs:
  https://dev.elsevier.com/documentation/ScienceDirectSearchAPI.wadl
  https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
"""
from __future__ import annotations

import logging
from typing import List, Optional

from config import get_settings
from models.paper import Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"
_ARTICLE_URL = "https://api.elsevier.com/content/article/doi/{doi}"


class ElsevierClient(BaseAPIClient):
    """Wrapper around the Elsevier ScienceDirect API."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        return {
            "X-ELS-APIKey": _settings.elsevier_api_key,
            "Accept": accept,
        }

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        if not _settings.elsevier_api_key:
            logger.info("Elsevier API key not set – skipping.")
            return []

        params = {
            "query": query,
            "count": min(max_results, 25),
            "field": "doi,title,creator,coverDate,description",
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Elsevier search failed: %s", exc)
            return []

        results = (
            data.get("search-results", {}).get("entry", [])
        )
        papers: list[Paper] = []
        for item in results:
            doi = item.get("prism:doi") or item.get("dc:identifier", "").replace("DOI:", "")
            papers.append(
                Paper(
                    doi=doi or None,
                    title=item.get("dc:title", "Untitled"),
                    authors=[item.get("dc:creator", "")] if item.get("dc:creator") else [],
                    abstract=item.get("dc:description"),
                    year=_year_from_date(item.get("prism:coverDate")),
                    source="elsevier",
                    url=item.get("link", [{}])[0].get("@href"),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[str]:
        if not _settings.elsevier_api_key or not paper.doi:
            return None
        url = _ARTICLE_URL.format(doi=paper.doi)
        try:
            resp = await self._get(url, headers=self._headers("text/plain"))
            return resp.text
        except Exception as exc:  # noqa: BLE001
            logger.warning("Elsevier full-text fetch failed for %s: %s", paper.doi, exc)
            return None


def _year_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(str(date_str)[:4])
    except (ValueError, TypeError):
        return None
