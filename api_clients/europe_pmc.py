"""Europe PMC API client.

Docs: https://europepmc.org/RestfulWebService
"""
from __future__ import annotations

import logging
from typing import List, Optional

from models.paper import FullText, FullTextFormat, Paper
from .base import BaseAPIClient

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
_FULL_TEXT_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/{source}/{pmcid}/fullTextXML"


class EuropePMCClient(BaseAPIClient):
    """Wrapper around the Europe PMC REST API."""

    RATE_CALLS = 10
    RATE_PERIOD = 1.0

    async def search(self, query: str, max_results: int = 10) -> List[Paper]:
        params = {
            "query": query,
            "format": "json",
            "pageSize": min(max_results, 25),
            "resultType": "core",
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
            title = item.get("title", "").strip() or "Untitled"
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

    async def fetch_full_text(self, paper: Paper) -> Optional[str]:
        """Fetch PMC XML full-text. Only works for open-access PMC articles."""
        if not paper.url:
            return None
        # URL is https://europepmc.org/article/PMC/PMCxxxxxxx for OA papers
        parts = paper.url.rstrip("/").split("/")
        pmc_id: Optional[str] = None
        if "PMC" in parts:
            idx = parts.index("PMC")
            if idx + 1 < len(parts):
                candidate = parts[idx + 1]
                if candidate.startswith("PMC") and candidate[3:].isdigit():
                    pmc_id = candidate

        if pmc_id:
            url = _FULL_TEXT_URL.format(source="PMC", pmcid=pmc_id)
            try:
                resp = await self._get(url)
                return resp.text
            except Exception as exc:  # noqa: BLE001
                logger.warning("EuropePMC full-text fetch failed for %s: %s", pmc_id, exc)
        return None


def _safe_int(value: object) -> Optional[int]:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
