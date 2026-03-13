"""Unpaywall API client.

Unpaywall resolves DOIs to open-access versions of papers.  It has **no**
search endpoint, so :py:meth:`search` always returns an empty list.  It is
used exclusively in the full-text retrieval phase.

Docs: https://unpaywall.org/products/api
"""
from __future__ import annotations

import logging
from typing import List, Optional

import base64

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)
_settings = get_settings()

_API_URL = "https://api.unpaywall.org/v2/{doi}"


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
                _API_URL.format(doi=paper.doi), params={"email": email}
            )
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unpaywall lookup failed for %s: %s", paper.doi, exc)
            return None

        # Prefer the best_oa_location's direct PDF URL; fall back to other locations
        pdf_url: Optional[str] = None
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf")
        if not pdf_url:
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    pdf_url = loc["url_for_pdf"]
                    break

        if not pdf_url:
            logger.debug("Unpaywall: no OA PDF found for %s", paper.doi)
            return None

        # Step 2: download the PDF
        try:
            pdf_bytes = await self._get_bytes(pdf_url)
            if not pdf_bytes:
                return None
            b64 = base64.b64encode(pdf_bytes).decode("ascii")
            return FullText(format=FullTextFormat.PDF, content=b64)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unpaywall PDF download failed for %s (%s): %s", paper.doi, pdf_url, exc
            )
            return None
