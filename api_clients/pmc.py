"""NCBI PubMed / PubMed Central (PMC) API client using Entrez E-utilities.

Docs:
  https://www.ncbi.nlm.nih.gov/books/NBK25499/   (E-utilities reference)
  https://www.ncbi.nlm.nih.gov/pmc/tools/developers/  (Open-Access subset)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time as _time
import xml.etree.ElementTree as ET
from typing import List, Optional

from config import get_settings
from models.paper import FullText, FullTextFormat, Paper
from utils.rate_limiter import get_shared_limiter
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)
_settings = get_settings()

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"
_MIN_BODY_CHARS = 3000
_MIN_BODY_PARAGRAPHS = 6

_TOOL = "Pipetly"
_EMAIL = "contact@pipetly.bot"
_PMCID_RE = re.compile(r"PMC\d+", re.IGNORECASE)


class PMCClient(BaseAPIClient):
    """Wrapper around the NCBI Entrez E-utilities for PubMed & PMC."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0
    RATE_LIMITER_KEY = "ncbi_eutils"
    _NCBI_SEMAPHORE = asyncio.Semaphore(5)
    _NCBI_MIN_DELAY = 0.1  # seconds between requests to avoid upstream throttling
    _NCBI_DELAY_LOCK = asyncio.Lock()
    _last_ncbi_request_ts: float = 0.0

    def _init_rate_limiter(self):
        calls = 10 if _settings.ncbi_api_key else 3
        return get_shared_limiter(self.RATE_LIMITER_KEY, calls=calls, period=self.RATE_PERIOD)

    async def _get(self, url: str, **kwargs: object):  # type: ignore[override]
        # NCBI throttles bursts; gate concurrency and add minimal spacing between calls.
        async with self._NCBI_SEMAPHORE:
            await self._ncbi_min_spacing()
            return await super()._get(url, **kwargs)

    async def _ncbi_min_spacing(self) -> None:
        async with self._NCBI_DELAY_LOCK:
            now = _time.monotonic()
            wait_for = self._NCBI_MIN_DELAY - (now - self._last_ncbi_request_ts)
            if wait_for > 0:
                await asyncio.sleep(wait_for)
            self._last_ncbi_request_ts = _time.monotonic()

    def _base_params(self) -> dict[str, str]:
        params = {"tool": _TOOL, "email": _EMAIL, "retmode": "json"}
        if _settings.ncbi_api_key:
            params["api_key"] = _settings.ncbi_api_key
        return params

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        # Search PubMed for article IDs
        search_params = {
            **self._base_params(),
            "db": "pubmed",
            "term": query,
            "retmax": str(min(max_results, 50)),
        }
        try:
            resp = await self._get(_ESEARCH_URL, params=search_params)
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("PMC/PubMed esearch failed: %s", exc)
            return []

        ids: list[str] = data.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Fetch summary records for those IDs
        summary_params = {
            **self._base_params(),
            "db": "pubmed",
            "id": ",".join(ids),
        }
        try:
            sresp = await self._get(_ESUMMARY_URL, params=summary_params)
            sdata = sresp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("PMC/PubMed esummary failed: %s", exc)
            return []

        papers: list[Paper] = []
        result_map = sdata.get("result", {})
        for uid in result_map.get("uids", []):
            item = result_map.get(uid, {})
            article_ids: list[dict] = item.get("articleids", [])
            doi = next(
                (a.get("value") for a in article_ids if a.get("idtype") == "doi"),
                None,
            )
            pmcid = next(
                (a.get("value") for a in article_ids if a.get("idtype") == "pmc"),
                None,
            )
            title = clean_title(item.get("title", ""))
            authors = [a.get("name", "") for a in item.get("authors", [])]
            year = _safe_int((item.get("pubdate") or "")[:4])
            papers.append(
                Paper(
                    doi=doi or None,
                    title=title,
                    authors=authors,
                    abstract=None,  # esummary does not include abstracts
                    year=year,
                    source="pmc",
                    url=(
                        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
                        if pmcid
                        else None
                    ),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Fetch full XML from the PMC Open-Access subset.

        Works for any PMC OA article; looks up the PMC ID by DOI via
        esearch when the stored URL is not a PMC URL.
        """
        pmc_id = _extract_pmcid_from_url(paper.url)

        if not pmc_id and paper.doi:
            # Use esearch to find the PMC article ID from the DOI
            try:
                resp = await self._get(
                    _ESEARCH_URL,
                    params={
                        **self._base_params(),
                        "db": "pmc",
                        "term": f"{paper.doi}[DOI]",
                        "retmax": "1",
                    },
                )
                ids = resp.json().get("esearchresult", {}).get("idlist", [])
                if ids:
                    pmc_id = f"PMC{ids[0]}"
            except Exception as exc:  # noqa: BLE001
                logger.debug("PMC DOI lookup failed for %s: %s", paper.doi, exc)

        if not pmc_id:
            return None

        # Try BioC (fast, OA subset) before Entrez efetch
        bioc_xml = await self._fetch_bioc_xml(pmc_id)
        if bioc_xml and _looks_like_fulltext_xml(bioc_xml):
            return FullText(format=FullTextFormat.XML, content=bioc_xml)

        params = {
            **self._base_params(),
            "db": "pmc",
            "id": pmc_id[3:] if pmc_id.upper().startswith("PMC") else pmc_id,
            "rettype": "full",
            "retmode": "xml",
        }
        try:
            resp = await self._get(_EFETCH_URL, params=params)
            xml_text = resp.text.strip()
            if not xml_text or "<html" in xml_text.lower():
                return None
            if not _looks_like_fulltext_xml(xml_text):
                logger.debug("PMC fetch returned non-full-text XML for %s", pmc_id)
                return None
            return FullText(format=FullTextFormat.XML, content=xml_text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PMC full-text fetch failed for %s: %s", pmc_id, exc)
            return None

    async def _fetch_bioc_xml(self, pmc_id: str) -> Optional[str]:
        """Fetch BioC XML for PMC OA articles; returns None on failure."""
        pmc_norm = pmc_id if pmc_id.upper().startswith("PMC") else f"PMC{pmc_id}"
        params = {"id": pmc_norm, "format": "xml"}
        try:
            resp = await self._get(_BIOC_URL, params=params)
            xml_text = resp.text.strip()
            # BioC returns short error payloads; require body tag or minimal length
            lower = xml_text.lower()
            if not xml_text or "<error" in lower or "<body" not in lower or len(xml_text) < 500:
                return None
            return xml_text
        except Exception as exc:  # noqa: BLE001
            logger.debug("BioC fetch failed for %s: %s", pmc_norm, exc)
            return None


def _extract_pmcid_from_url(url: Optional[str]) -> Optional[str]:
    """Extract a PMCxxxxxxx identifier from any URL or string containing it."""
    if not url:
        return None
    match = _PMCID_RE.search(url)
    if match:
        return match.group(0).upper()
    return None


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _looks_like_fulltext_xml(xml_text: str) -> bool:
    """Return True when XML contains a substantial article body."""
    lower = xml_text.lower()
    body_chars, body_paragraphs = _jats_body_metrics(xml_text)
    if body_paragraphs > 0:
        return body_chars >= _MIN_BODY_CHARS or body_paragraphs >= _MIN_BODY_PARAGRAPHS

    # BioC payloads can omit <body>; use a conservative text-length fallback.
    if "<collection" in lower and "<passage" in lower:
        return len(_strip_xml_tags(xml_text)) >= 6000

    return False


def _jats_body_metrics(xml_text: str) -> tuple[int, int]:
    """Extract body text length and paragraph count from JATS-like XML."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return 0, 0

    body = root.find(".//{*}body")
    if body is None:
        return 0, 0

    body_parts = [text.strip() for text in body.itertext() if text and text.strip()]
    body_text = " ".join(body_parts)
    body_paragraphs = len(body.findall(".//{*}p"))
    return len(body_text), body_paragraphs


def _strip_xml_tags(xml_text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml_text)).strip()
