"""Semantic Scholar API client.

Docs: https://api.semanticscholar.org/api-docs/
"""
from __future__ import annotations

import logging
from typing import List, Optional

import base64
from urllib.parse import urlparse

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from utils.rate_limiter import get_shared_limiter
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
_FIELDS = "paperId,externalIds,title,abstract,year,authors,openAccessPdf"
_PDF_BLOCKLIST = {
    "onlinelibrary.wiley.com",
    "wiley.com",
    "academic.oup.com",
    "oup.com",
    "oxfordjournals.org",
}


class SemanticScholarClient(BaseAPIClient):
    """Wrapper around the Semantic Scholar Graph API."""

    RATE_CALLS = 5
    RATE_PERIOD = 1.0
    RATE_LIMITER_KEY = "semantic_scholar"
    STARTUP_JITTER_MAX = 0.2

    def _init_rate_limiter(self):
        calls = 5 if _settings.semantic_scholar_api_key else 1
        return get_shared_limiter(self.RATE_LIMITER_KEY, calls=calls, period=self.RATE_PERIOD)

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
                    title=clean_title(item.get("title", "")),
                    authors=[a.get("name", "") for a in item.get("authors", [])],
                    abstract=item.get("abstract"),
                    year=item.get("year"),
                    source="semantic_scholar",
                    url=(item.get("openAccessPdf") or {}).get("url"),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Look up the paper's open-access PDF URL via DOI, then download it.

        For papers from any source, performs a DOI-based lookup against
        Semantic Scholar to discover an ``openAccessPdf`` URL.  Falls back
        to the stored ``paper.url`` only for papers sourced from S2.
        """
        pdf_url: Optional[str] = None

        if paper.doi:
            try:
                resp = await self._get(
                    _PAPER_URL.format(paper_id=f"DOI:{paper.doi}"),
                    params={"fields": "openAccessPdf"},
                    headers=self._headers(),
                )
                data = resp.json()
                pdf_url = (data.get("openAccessPdf") or {}).get("url")
            except Exception as exc:  # noqa: BLE001
                logger.debug("SemanticScholar DOI lookup failed for %s: %s", paper.doi, exc)

        # Only fall back to the stored URL when it came from Semantic Scholar
        if not pdf_url and paper.source == "semantic_scholar":
            pdf_url = paper.url

        if not pdf_url:
            return None

        host = urlparse(pdf_url).hostname or ""
        if any(host.endswith(blocked) for blocked in _PDF_BLOCKLIST):
            logger.debug("SemanticScholar: skipping blocked PDF host %s", host)
            return None

        try:
            pdf_bytes = await self._get_bytes(pdf_url)
            if not pdf_bytes:
                return None
            b64 = base64.b64encode(pdf_bytes).decode("ascii")
            return FullText(format=FullTextFormat.PDF, content=b64)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SemanticScholar full-text fetch failed: %s", exc)
            return None
