"""Elsevier / ScienceDirect API client.

Docs:
  https://dev.elsevier.com/documentation/ScienceDirectSearchAPI.wadl
  https://dev.elsevier.com/documentation/ArticleRetrievalAPI.wadl
"""

from __future__ import annotations

import logging
from typing import List, Optional

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"
_ARTICLE_URL = "https://api.elsevier.com/content/article/doi/{doi}"


class ElsevierClient(BaseAPIClient):
    """Wrapper around the Elsevier ScienceDirect API."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0

    def _headers(self, accept: str = "application/json") -> dict[str, str]:
        headers = {
            "X-ELS-APIKey": _settings.elsevier_api_key,
            "Accept": accept,
        }
        if _settings.elsevier_inst_token:
            headers["X-ELS-Insttoken"] = _settings.elsevier_inst_token
        return headers

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        if not _settings.elsevier_api_key:
            logger.info("Elsevier API key not set – skipping.")
            return []

        params = {
            "query": query,
            "count": min(max_results, 25),
            "field": "doi,title,creator,authors,coverDate,description",
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Elsevier search failed: %s", exc)
            return []

        results = data.get("search-results", {}).get("entry", [])
        if isinstance(results, dict):
            results = [results]

        papers: list[Paper] = []
        for item in results:
            if not isinstance(item, dict):
                continue
                
            doi = item.get("prism:doi") or item.get("dc:identifier", "").replace("DOI:", "")
            
            raw_authors = (item.get("authors") or {}).get("author", [])
            if isinstance(raw_authors, dict):
                raw_authors = [raw_authors]
                
            if raw_authors and isinstance(raw_authors, list):
                authors = [
                    (
                        f"{a.get('given-name', '')} {a.get('surname', '')}".strip()
                        or a.get("$", "")
                    ).strip()
                    for a in raw_authors
                    if isinstance(a, dict) and (a.get("given-name") or a.get("surname") or a.get("$"))
                ]
            else:
                creator = item.get("dc:creator", "")
                authors = [creator] if creator else []
                
            raw_links = item.get("link", [])
            if isinstance(raw_links, dict):
                raw_links = [raw_links]
            url = raw_links[0].get("@href") if raw_links and isinstance(raw_links, list) and isinstance(raw_links[0], dict) else None

            papers.append(
                Paper(
                    doi=doi or None,
                    title=clean_title(item.get("dc:title", "")),
                    authors=authors,
                    abstract=item.get("dc:description"),
                    year=_year_from_date(item.get("prism:coverDate")),
                    source="elsevier",
                    url=url,
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        if not _settings.elsevier_api_key or not paper.doi:
            return None
        if not _is_elsevier_doi(paper.doi):
            logger.debug(
                "Skipping Elsevier full-text fetch for non-Elsevier DOI: %s", paper.doi
            )
            return None
        url = _ARTICLE_URL.format(doi=paper.doi)
        try:
            resp = await self._get(url, headers=self._headers("text/plain"))
            text = resp.text.strip()
            if not text:
                return None
            return FullText(format=FullTextFormat.PLAIN, content=text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Elsevier full-text fetch failed for %s: %s", paper.doi, exc)
            return None


def _year_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        return int(str(date_str)[:4])
    except (ValueError, TypeError):
        return None


def _is_elsevier_doi(doi: str) -> bool:
    """Return True when the DOI belongs to Elsevier (10.1016/*)."""
    normalized = doi.strip().lower()
    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    )
    for pfx in prefixes:
        if normalized.startswith(pfx):
            normalized = normalized[len(pfx) :]
            break
    return normalized.startswith("10.1016/")
