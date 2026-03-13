"""NCBI PubMed / PubMed Central (PMC) API client using Entrez E-utilities.

Docs:
  https://www.ncbi.nlm.nih.gov/books/NBK25499/   (E-utilities reference)
  https://www.ncbi.nlm.nih.gov/pmc/tools/developers/  (Open-Access subset)
"""
from __future__ import annotations

import logging
from typing import List, Optional

from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

_ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
_ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_TOOL = "Pipetly"
_EMAIL = "contact@pipetly.bot"


class PMCClient(BaseAPIClient):
    """Wrapper around the NCBI Entrez E-utilities for PubMed & PMC."""

    RATE_CALLS = 3
    RATE_PERIOD = 1.0

    def _base_params(self) -> dict[str, str]:
        return {"tool": _TOOL, "email": _EMAIL, "retmode": "json"}

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
            title = item.get("title", "Untitled")
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

        params = {
            "tool": _TOOL,
            "email": _EMAIL,
            "db": "pmc",
            "id": pmc_id[3:] if pmc_id.upper().startswith("PMC") else pmc_id,
            "rettype": "full",
            "retmode": "xml",
        }
        try:
            resp = await self._get(_EFETCH_URL, params=params)
            xml_text = resp.text.strip()
            if not xml_text:
                return None
            return FullText(format=FullTextFormat.XML, content=xml_text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PMC full-text fetch failed for %s: %s", pmc_id, exc)
            return None


def _extract_pmcid_from_url(url: Optional[str]) -> Optional[str]:
    """Extract a PMCxxxxxxx identifier from a stored PubMed Central URL."""
    if not url or "pmc/articles" not in url:
        return None
    parts = url.rstrip("/").split("/")
    for part in reversed(parts):
        if part.upper().startswith("PMC") and part[3:].isdigit():
            return part
    return None


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
