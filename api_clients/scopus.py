"""Scopus (Elsevier) bibliographic search API client.

Scopus is a pure metadata/abstract database and does **not** provide full-text
access via its API.  It uses the same ``ELSEVIER_API_KEY`` as the ScienceDirect
client.

Docs:
  https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl
"""
from __future__ import annotations

import logging
from typing import List, Optional

from config import get_settings
from models.paper import FullText, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"


class ScopusClient(BaseAPIClient):
    """Wrapper around the Elsevier Scopus Search API."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        return {
            "X-ELS-APIKey": _settings.elsevier_api_key,
            "Accept": "application/json",
        }

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        if not _settings.elsevier_api_key:
            logger.info("Elsevier API key not set – skipping Scopus.")
            return []

        params = {
            "query": query,
            "count": min(max_results, 25),
            "field": "prism:doi,dc:title,dc:creator,author,prism:coverDate,dc:description,prism:url",
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("Scopus search failed: %s", exc)
            return []

        results = data.get("search-results", {}).get("entry", [])
        papers: list[Paper] = []
        for item in results:
            doi = (
                item.get("prism:doi")
                or item.get("dc:identifier", "").replace("DOI:", "").strip()
                or None
            )
            title = item.get("dc:title", "Untitled")
            raw_authors = item.get("author", [])
            if raw_authors:
                authors = [
                    (
                        f"{a.get('given-name', '')} {a.get('surname', '')}".strip()
                        or a.get("authname", "")
                    ).strip()
                    for a in raw_authors
                    if a.get("given-name") or a.get("surname") or a.get("authname")
                ]
            else:
                creator = item.get("dc:creator", "")
                authors = [creator] if creator else []
            papers.append(
                Paper(
                    doi=doi if doi else None,
                    title=title,
                    authors=authors,
                    abstract=item.get("dc:description"),
                    year=_year_from_date(item.get("prism:coverDate")),
                    source="scopus",
                    url=f"https://doi.org/{doi}" if doi else item.get("prism:url"),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Scopus is a metadata-only database; full text is not available here."""
        return None


def _year_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(str(date_str)[:4])
    except (ValueError, TypeError):
        return None
