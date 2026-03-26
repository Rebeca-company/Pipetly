"""Europe PMC API client.

Docs: https://europepmc.org/RestfulWebService
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient, clean_title

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_FULL_TEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"


class EuropePMCClient(BaseAPIClient):
    """Wrapper around the Europe PMC REST API."""

    RATE_CALLS = 10
    RATE_PERIOD = 1.0

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "query": query,
            "format": "json",
            "pageSize": min(max_results, 25),
            "resultType": "core",  # "idlist" only returns IDs; "core" includes title/authors/abstract/year
        }
        try:
            resp = await self._get(_SEARCH_URL, params=params)
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.error("EuropePMC search failed: %s", exc)
            return []

        papers: list[Paper] = []
        for item in data.get("resultList", {}).get("result", []):
            doi = item.get("doi") or None
            title = clean_title(item.get("title", ""))
            # Use the pmcid field directly; fall back to id only when source==PMC
            pmcid = item.get("pmcid") or (
                item.get("id") if item.get("source") == "PMC" else None
            )
            papers.append(
                Paper(
                    doi=doi,
                    title=title,
                    authors=[
                        a.get("fullName", "")
                        for a in item.get("authorList", {}).get("author", [])
                    ],
                    abstract=item.get("abstractText"),
                    year=_safe_int(item.get("pubYear")),
                    source="europe_pmc",
                    # Store the PMCID (if any) as the URL so fetch_full_text can use it
                    url=(
                        f"https://europepmc.org/article/PMC/{pmcid}"
                        if pmcid
                        else f"https://europepmc.org/article/{item.get('source', 'MED')}/{item.get('id', '')}"
                    ),
                )
            )
        return papers

    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Fetch PMC XML full-text. Works for any open-access PMC article;
        looks up the PMCID by DOI when the stored URL is not a PMC URL."""
        pmc_id = _extract_pmcid(paper.url)

        if not pmc_id and paper.doi:
            # Search Europe PMC by DOI to find the PMCID
            try:
                resp = await self._get(
                    _SEARCH_URL,
                    params={
                        "query": f"DOI:{paper.doi}",
                        "format": "json",
                        "pageSize": "1",
                        "resultType": "core",
                    },
                )
                results = resp.json().get("resultList", {}).get("result", [])
                if results:
                    hit = results[0]
                    pmc_id = hit.get("pmcid") or (
                        hit.get("id") if hit.get("source") == "PMC" else None
                    )
            except Exception as exc:  # noqa: BLE001
                logger.debug("EuropePMC DOI lookup failed for %s: %s", paper.doi, exc)

        if not pmc_id:
            return None

        url = _FULL_TEXT_URL.format(pmcid=pmc_id)
        try:
            resp = await self._get(url)
            xml_text = resp.text.strip()
            if not xml_text:
                return None
            return FullText(format=FullTextFormat.XML, content=xml_text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("EuropePMC full-text fetch failed for %s: %s", pmc_id, exc)
        return None


def _extract_pmcid(url: Optional[str]) -> Optional[str]:
    """Extract a PMCxxxxxxx identifier from any known article URL pattern."""
    if not url:
        return None
    match = re.search(r"PMC\d+", url, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
