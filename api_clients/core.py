"""CORE API client.

CORE aggregates open-access research outputs from repositories worldwide.
It supports both search and full-text download.

Docs: https://api.core.ac.uk/docs/v3
"""
from __future__ import annotations

import base64
import logging
from typing import List, Optional

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.core.ac.uk/v3/search/works"
_DOI_URL = "https://api.core.ac.uk/v3/works/doi:{doi}"
_DOWNLOAD_URL = "https://api.core.ac.uk/v3/outputs/{output_id}/download"


class COREClient(BaseAPIClient):
    """Wrapper around the CORE API v3."""

    RATE_CALLS = 5
    RATE_PERIOD = 1.0

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if _settings.core_api_key:
            headers["Authorization"] = f"Bearer {_settings.core_api_key}"
        return headers

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "q": query,
            "limit": str(min(max_results, 100)),
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params, headers=self._headers())
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("CORE search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("results", []):
            doi = item.get("doi") or None
            if doi:
                doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
            download_url = item.get("downloadUrl")
            source_urls: list[str] = item.get("sourceFulltextUrls") or []
            url = download_url or (source_urls[0] if source_urls else None)
            papers.append(
                Paper(
                    doi=doi or None,
                    title=item.get("title", "Untitled"),
                    authors=[a.get("name", "") for a in (item.get("authors") or [])],
                    abstract=item.get("abstract"),
                    year=_safe_int(item.get("yearPublished")),
                    source="core",
                    url=url,
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """
        Fetch full text via CORE's DOI-based lookup or the stored download URL.

        Requires ``CORE_API_KEY`` to be set for authenticated access.
        """
        if not _settings.core_api_key:
            logger.info("CORE_API_KEY not set – skipping CORE full-text.")
            return None

        # Strategy 1: look up the work by DOI to discover the download URL / output ID
        if paper.doi:
            try:
                resp = await self._get(
                    _DOI_URL.format(doi=paper.doi), headers=self._headers()
                )
                work = resp.json()
                download_url: Optional[str] = work.get("downloadUrl")
                output_id: Optional[str | int] = work.get("id")

                if download_url:
                    result = await self._fetch_url_as_fulltext(download_url)
                    if result:
                        return result

                if output_id:
                    result = await self._fetch_url_as_fulltext(
                        _DOWNLOAD_URL.format(output_id=output_id),
                        extra_headers=self._headers(),
                    )
                    if result:
                        return result
            except Exception as exc:  # noqa: BLE001
                logger.warning("CORE DOI lookup failed for %s: %s", paper.doi, exc)

        # Strategy 2: use the URL already stored in the paper (only if it came from CORE)
        if paper.url and paper.source == "core":
            return await self._fetch_url_as_fulltext(paper.url)

        return None

    async def _fetch_url_as_fulltext(
        self, url: str, extra_headers: Optional[dict] = None
    ) -> Optional[FullText]:
        """Download *url* and wrap the content in a :class:`FullText` object."""
        try:
            raw_bytes = await self._get_bytes(url, **(dict(headers=extra_headers) if extra_headers else {}))
            if not raw_bytes:
                return None
            if raw_bytes[:4] == b"%PDF":
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                return FullText(format=FullTextFormat.PDF, content=b64)
            text = raw_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return None
            fmt = (
                FullTextFormat.XML
                if text.lstrip().startswith("<")
                else FullTextFormat.PLAIN
            )
            return FullText(format=fmt, content=text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("CORE URL fetch failed for %s: %s", url, exc)
            return None


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
