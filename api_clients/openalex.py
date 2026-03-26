"""OpenAlex API client.

Docs: https://docs.openalex.org/
"""
from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import quote

import base64

from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient, clean_title

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
            title = clean_title(item.get("title", ""))
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

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Find the OA URL via DOI lookup, then download the content.

        For papers from any source, performs a DOI-based lookup against
        OpenAlex to discover an open-access URL.  Falls back to the stored
        ``paper.url`` only for papers already sourced from OpenAlex.
        """
        oa_url: Optional[str] = None

        if paper.doi:
            try:
                resp = await self._get(
                    _SINGLE_WORK_URL.format(doi=paper.doi),
                    params={"select": "open_access,primary_location"},
                    headers=self._headers(),
                )
                data = resp.json()
                oa_url = (
                    (data.get("open_access") or {}).get("oa_url")
                    or (data.get("primary_location") or {}).get("landing_page_url")
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("OpenAlex DOI lookup failed for %s: %s", paper.doi, exc)

        # Only fall back to the stored URL when it actually came from OpenAlex
        if not oa_url and paper.source == "openalex":
            oa_url = paper.url

        if not oa_url:
            return None

        try:
            raw_bytes = await self._get_bytes(oa_url)

            # Robust PDF detection: look for %PDF after optional whitespace/BOM in first KB
            probe = raw_bytes[:1024].lstrip(b"\r\n\t \ufeff")
            if b"%PDF" in probe[:20]:
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                return FullText(format=FullTextFormat.PDF, content=b64)

            text = raw_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return None

            head = text[:200].lower().lstrip()
            is_html = head.startswith("<") and ("<html" in head or "<!doctype" in head)
            fmt = FullTextFormat.HTML if is_html else FullTextFormat.PLAIN
            return FullText(format=fmt, content=text)
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
