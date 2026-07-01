"""Unpaywall API client.

Unpaywall resolves DOIs to open-access versions of papers.  It has **no**
search endpoint, so :py:meth:`search` always returns an empty list.  It is
used exclusively in the full-text retrieval phase.

Docs: https://unpaywall.org/products/api
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import quote

import base64

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_API_URL = "https://api.unpaywall.org/v2/{doi}"
_MIN_TEXT_CHARS = 4000
_PREVIEW_MARKERS = (
    "sign in",
    "purchase",
    "subscribe",
    "access through your institution",
    "buy article",
    "redirecting",
)


class UnpaywallClient(BaseAPIClient):
    """Wrapper around the Unpaywall REST API (full-text retrieval only)."""

    RATE_CALLS = 5
    RATE_PERIOD = 1.0

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        """Unpaywall has no search endpoint; always returns an empty list."""
        return []

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """
        Look up the DOI in Unpaywall and download the best open-access PDF.

        Requires ``UNPAYWALL_EMAIL`` to be set in the environment / .env file.
        """
        if not paper.doi:
            return None

        email = _settings.unpaywall_email
        if not email:
            logger.info("UNPAYWALL_EMAIL not set – skipping Unpaywall full-text.")
            return None

        # Step 1: resolve the DOI to the best OA location
        try:
            resp = await self._get(
                _API_URL.format(doi=quote(paper.doi, safe="")), params={"email": email}
            )
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Unpaywall lookup failed for %s: %s", paper.doi, exc)
            return None

        # Prefer direct PDF URLs, then try OA landing/fulltext links.
        candidates: list[str] = []

        def _push(url: Optional[str]) -> None:
            if url and url not in candidates:
                candidates.append(url)

        best = data.get("best_oa_location") or {}
        _push(best.get("url_for_pdf"))
        _push(best.get("url"))
        _push(best.get("url_for_landing_page"))

        for loc in data.get("oa_locations", []):
            _push(loc.get("url_for_pdf"))
            _push(loc.get("url"))
            _push(loc.get("url_for_landing_page"))

        if not candidates:
            logger.debug("Unpaywall: no OA URL candidates found for %s", paper.doi)
            return None

        # Step 2: download from candidates until one yields usable full text.
        for url in candidates:
            try:
                result = await self._download_candidate(url)
                if result is not None:
                    return result
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "Unpaywall candidate failed for %s (%s): %s", paper.doi, url, exc
                )

        return None

    async def _download_candidate(self, url: str) -> Optional[FullText]:
        raw_bytes = await self._get_bytes(url)
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
            len(_strip_tags_and_normalise(text)) if is_html else len(_collapse_ws(text))
        )
        if _looks_like_preview(text, plain_len):
            return None

        fmt = FullTextFormat.HTML if is_html else FullTextFormat.PLAIN
        return FullText(format=fmt, content=text)


def _looks_like_preview(text: str, plain_len: int) -> bool:
    body = text[:8000].lower()
    marker_hits = sum(1 for marker in _PREVIEW_MARKERS if marker in body)
    return marker_hits >= 2 or plain_len < _MIN_TEXT_CHARS


def _strip_tags_and_normalise(text: str) -> str:
    no_scripts = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\\1>", " ", text)
    no_head = re.sub(r"(?is)<head[^>]*>.*?</head>", " ", no_scripts)
    return _collapse_ws(re.sub(r"<[^>]+>", " ", no_head))


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
