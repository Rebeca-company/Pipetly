"""OpenAlex API client.

Docs: https://docs.openalex.org/
"""
from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import quote

from models.paper import Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

_WORKS_URL = "https://api.openalex.org/works"
_SINGLE_WORK_URL = "https://api.openalex.org/works/doi:{doi}"
_SELECT = "id,doi,title,authorships,abstract_inverted_index,publication_year,open_access,primary_location"


class OpenAlexClient(BaseAPIClient):
    """Wrapper around the OpenAlex REST API."""

    RATE_CALLS = 10
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "Pipetly/1.0 (mailto:contact@pipetly.bot)"}

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "search": query,
            "per-page": min(max_results, 50),
            "select": _SELECT,
        }
        try:
            resp = await self._get(_WORKS_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("OpenAlex search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("results", []):
            doi = (item.get("doi") or "").replace("https://doi.org/", "") or None
            title = item.get("title", "Untitled")
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in item.get("authorships", [])
            ]
            abstract = _rebuild_abstract(item.get("abstract_inverted_index"))
            oa_url = (
                (item.get("open_access") or {}).get("oa_url")
                or (item.get("primary_location") or {}).get("landing_page_url")
            )
            papers.append(
                Paper(
                    doi=doi,
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=item.get("publication_year"),
                    source="openalex",
                    url=oa_url,
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[str]:
        """Attempt to fetch open-access PDF text via the OA URL."""
        if not paper.url:
            return None
        try:
            resp = await self._get(paper.url)
            ct = resp.headers.get("content-type", "")
            if "pdf" in ct.lower():
                # Return raw bytes string; caller should use a PDF extractor
                return resp.text
            return resp.text
        except Exception as exc:  # noqa: BLE001
            logger.warning("OpenAlex full-text fetch failed for %s: %s", paper.doi, exc)
            return None


def _rebuild_abstract(inverted_index: Optional[dict]) -> Optional[str]:
    """Reconstruct abstract text from OpenAlex inverted index."""
    if not inverted_index:
        return None
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    if not words:
        return None
    return " ".join(words[i] for i in sorted(words))
