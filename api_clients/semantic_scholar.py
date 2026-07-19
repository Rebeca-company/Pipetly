"""Semantic Scholar API client.

Docs: https://api.semanticscholar.org/api-docs/
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import base64
from urllib.parse import quote, urlparse

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from utils.rate_limiter import get_shared_limiter
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)
_settings = get_settings()

_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
_FIELDS = "paperId,externalIds,title,abstract,year,authors,openAccessPdf"
_FT_FIELDS = "openAccessPdf,url"
_PDF_BLOCKLIST = {
    "onlinelibrary.wiley.com",
    "wiley.com",
    "academic.oup.com",
    "oup.com",
    "oxfordjournals.org",
}
_MIN_TEXT_CHARS = 4000
_PREVIEW_MARKERS = (
    "sign in",
    "purchase",
    "subscribe",
    "access through your institution",
    "buy article",
    "redirecting",
)


class SemanticScholarClient(BaseAPIClient):
    """Wrapper around the Semantic Scholar Graph API."""

    RATE_CALLS = 5
    RATE_PERIOD = 1.0
    RATE_LIMITER_KEY = "semantic_scholar"
    STARTUP_JITTER_MAX = 0.2

    def _init_rate_limiter(self):
        calls = 5 if _settings.semantic_scholar_api_key else 1
        return get_shared_limiter(
            self.RATE_LIMITER_KEY, calls=calls, period=self.RATE_PERIOD
        )

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
            logger.debug("SemanticScholar search failed: %s", exc)
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
        """Look up the paper's open-access PDF URL via DOI, then download it."""
        candidate_url: Optional[str] = None

        if paper.doi:
            doi_id = quote(paper.doi, safe="")
            try:
                resp = await self._get(
                    _PAPER_URL.format(paper_id=f"DOI:{doi_id}"),
                    params={"fields": _FT_FIELDS},
                    headers=self._headers(),
                )
                data = resp.json()
                candidate_url = (data.get("openAccessPdf") or {}).get(
                    "url"
                ) or data.get("url")
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "SemanticScholar DOI lookup failed for %s: %s", paper.doi, exc
                )

            # Fallback: search endpoint can still return a usable OA URL when DOI lookup misses.
            if not candidate_url:
                try:
                    sresp = await self._get(
                        _SEARCH_URL,
                        params={"query": paper.doi, "limit": 1, "fields": _FT_FIELDS},
                        headers=self._headers(),
                    )
                    results = sresp.json().get("data", [])
                    if results:
                        item = results[0]
                        candidate_url = (item.get("openAccessPdf") or {}).get(
                            "url"
                        ) or item.get("url")
                except Exception as exc:  # noqa: BLE001
                    logger.debug(
                        "SemanticScholar DOI search fallback failed for %s: %s",
                        paper.doi,
                        exc,
                    )

        # Only fall back to the stored URL when it came from Semantic Scholar
        if not candidate_url and paper.source == "semantic_scholar":
            candidate_url = paper.url

        # Cross-source fallback: if another search client already found a URL, try it too.
        if not candidate_url and paper.url:
            candidate_url = paper.url

        if not candidate_url:
            return None

        host = urlparse(candidate_url).hostname or ""
        if any(host.endswith(blocked) for blocked in _PDF_BLOCKLIST):
            logger.debug("SemanticScholar: skipping blocked PDF host %s", host)
            return None

        try:
            raw_bytes = await self._get_bytes(candidate_url)
            if not raw_bytes:
                return None

            probe = raw_bytes[:1024].lstrip(b"\xef\xbb\xbf\r\n\t ")
            if probe.startswith(b"%PDF"):
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                return FullText(format=FullTextFormat.PDF, content=b64)

            text = raw_bytes.decode("utf-8", errors="replace").strip()
            if not text:
                return None

            head = text[:3000].lower().lstrip()
            is_html = head.startswith("<") and ("<html" in head or "<!doctype" in head)
            plain_len = (
                len(_strip_tags_and_normalise(text))
                if is_html
                else len(_collapse_ws(text))
            )
            if _looks_like_preview(text, plain_len):
                return None

            fmt = FullTextFormat.HTML if is_html else FullTextFormat.PLAIN
            return FullText(format=fmt, content=text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("SemanticScholar full-text fetch failed: %s", exc)
            return None


def _looks_like_preview(text: str, plain_len: int) -> bool:
    head = text[:8000].lower()
    marker_hits = sum(1 for marker in _PREVIEW_MARKERS if marker in head)
    return marker_hits >= 2 or plain_len < _MIN_TEXT_CHARS


def _strip_tags_and_normalise(text: str) -> str:
    no_scripts = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\\1>", " ", text)
    no_head = re.sub(r"(?is)<head[^>]*>.*?</head>", " ", no_scripts)
    return _collapse_ws(re.sub(r"<[^>]+>", " ", no_head))


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
