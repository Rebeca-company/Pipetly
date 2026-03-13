"""CrossRef API client.

Docs: https://api.crossref.org/swagger-ui/index.html
"""
from __future__ import annotations

import logging
from typing import List, Optional

from models.paper import FullText, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://api.crossref.org/works"
_DOI_URL = "https://api.crossref.org/works/{doi}"


class CrossRefClient(BaseAPIClient):
    """Wrapper around the CrossRef REST API."""

    RATE_CALLS = 5
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        # Polite pool: add a contact email via User-Agent
        return {"User-Agent": "Pipetly/1.0 (mailto:contact@pipetly.bot)"}

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "query": query,
            "rows": min(max_results, 50),
            "select": "DOI,title,author,abstract,published,URL",
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("CrossRef search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("message", {}).get("items", []):
            doi = item.get("DOI")
            titles = item.get("title", [])
            title = titles[0] if titles else "Untitled"
            authors = [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in item.get("author", [])
            ]
            year_parts = (item.get("published") or {}).get("date-parts", [[None]])
            year = year_parts[0][0] if year_parts and year_parts[0] else None
            papers.append(
                Paper(
                    doi=doi,
                    title=title,
                    authors=authors,
                    abstract=item.get("abstract"),
                    year=year,
                    source="crossref",
                    url=item.get("URL"),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """CrossRef doesn't host full text; leave full-text fetch to other clients."""
        return None

    async def resolve_doi(self, doi: str) -> Optional[Paper]:
        """Fetch structured metadata for a specific DOI."""
        url = _DOI_URL.format(doi=doi)
        try:
            resp = await self._get(url, headers=self._headers())
            item = resp.json().get("message", {})
        except Exception as exc:  # noqa: BLE001
            logger.warning("CrossRef DOI resolution failed for %s: %s", doi, exc)
            return None

        titles = item.get("title", [])
        title = titles[0] if titles else "Untitled"
        authors = [
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in item.get("author", [])
        ]
        year_parts = (item.get("published") or {}).get("date-parts", [[None]])
        year = year_parts[0][0] if year_parts and year_parts[0] else None
        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            abstract=item.get("abstract"),
            year=year,
            source="crossref",
            url=item.get("URL"),
        )
