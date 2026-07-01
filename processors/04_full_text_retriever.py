"""Step 4 – Full-Text Retrieval.

For every filtered paper, try all configured API clients in priority order and
store the first successful retrieval as a raw :class:`~models.paper.FullText`
object (PDF base-64, XML, HTML, or plain text).

Text extraction and format conversion happen in Step 5
(:mod:`processors.text_extractor`).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time as _time
from typing import List, Optional, Tuple

from api_clients import (
    ElsevierClient,
    EuropePMCClient,
    PMCClient,
    UnpaywallClient,
    SemanticScholarClient,
    OpenAlexClient,
)
from models.paper import FullText, Paper

logger = logging.getLogger(__name__)


class FullTextRetriever:
    """Step 4: attempt to fetch raw full-text for each paper from all sources."""

    # Priority order: open-access XML sources first, then PDF sources
    _CLIENT_ORDER = [
        ElsevierClient,
        EuropePMCClient,
        PMCClient,
        SemanticScholarClient,
        UnpaywallClient,
        OpenAlexClient,
    ]

    async def retrieve(self, papers: List[Paper]) -> List[Paper]:
        """
        For each paper in *papers*, query every API client until one returns
        a non-empty :class:`FullText`. The raw content (PDF, XML, HTML, or
        plain text) is stored in ``paper.full_text`` for later extraction.

        Returns only papers for which full text could be retrieved.
        """
        self._api_fetches = 0
        async with contextlib.AsyncExitStack() as stack:
            all_clients = [
                await stack.enter_async_context(cls()) for cls in self._CLIENT_ORDER
            ]

            key_to_papers: dict[str, List[Paper]] = {}
            canonical_papers: list[Paper] = []
            canonical_keys: list[str] = []

            for paper in papers:
                key = _paper_dedup_key(paper)
                if key not in key_to_papers:
                    key_to_papers[key] = [paper]
                    canonical_papers.append(paper)
                    canonical_keys.append(key)
                else:
                    key_to_papers[key].append(paper)

            tasks = [
                _fetch_first_available(all_clients, paper)
                for paper in canonical_papers
            ]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        success = 0
        failure = 0
        for key, paper, result in zip(canonical_keys, canonical_papers, raw_results):
            target_group = key_to_papers.get(key, [paper])
            if isinstance(result, tuple):
                ft, client_name, elapsed_ms, attempts = result
                for target in target_group:
                    target.ft_attempts = attempts
                
                if ft is not None:
                    success += 1
                    for target in target_group:
                        target.full_text = ft
                        target.ft_retrieved_by = client_name
                        target.ft_response_time_ms = elapsed_ms
                else:
                    failure += 1
            elif isinstance(result, Exception):
                failure += 1
                logger.warning(
                    "Full-text retrieval error for '%s': %s",
                    paper.title[:60],
                    result,
                )

        papers_with_full_text = [
            p for p in papers if p.full_text is not None and p.full_text.content.strip()
        ]
        logger.info(
            "Full-text retrieval: %d successes, %d failures (out of %d total fetches)",
            success,
            failure,
            self._api_fetches,
        )
        return papers_with_full_text


# Maps the class name suffix to a short source label used in the Paper model
_CLIENT_LABELS = {
    "EuropePMCClient": "europe_pmc",
    "PMCClient": "pmc",
    "ElsevierClient": "elsevier",
    "UnpaywallClient": "unpaywall",
    "OpenAlexClient": "openalex",
    "SemanticScholarClient": "semantic_scholar",
}

_PMCID_RE = re.compile(r"PMC\d+", re.IGNORECASE)
_DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)


def _canonical_doi(doi: str) -> str:
    normalized = _DOI_PREFIX_RE.sub("", doi.strip()).strip().lower()
    return normalized.rstrip("/.")


def _paper_dedup_key(paper: Paper) -> str:
    """Return a stable key for deduplicating fetch requests."""
    if paper.doi:
        return f"doi:{_canonical_doi(paper.doi)}"
    if paper.url:
        match = _PMCID_RE.search(paper.url)
        if match:
            return f"pmcid:{match.group(0).upper()}"
    return f"unique:{id(paper)}"


async def _fetch_first_available(
    clients: list, paper: Paper
) -> Tuple[Optional[FullText], Optional[str], Optional[float], List[dict]]:
    """Try each client in sequence; return (FullText, client_label, elapsed_ms, attempts)."""
    attempts = []
    for client in clients:
        client_name = type(client).__name__
        label = _CLIENT_LABELS.get(client_name, client_name)
        t0 = _time.monotonic()
        try:
            ft = await client.fetch_full_text(paper)  # type: ignore[attr-defined]
            elapsed_ms = round((_time.monotonic() - t0) * 1000, 1)
            
            if ft is not None and ft.content.strip():
                attempts.append({"client": label, "status": "success", "elapsed_ms": elapsed_ms})
                return ft, label, elapsed_ms, attempts
            else:
                attempts.append({"client": label, "status": "failure", "elapsed_ms": elapsed_ms})
                
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = round((_time.monotonic() - t0) * 1000, 1)
            attempts.append({"client": label, "status": "error", "elapsed_ms": elapsed_ms})
            logger.debug(
                "Full-text probe failed for '%s' via %s (%.0f ms): %s",
                paper.title[:60],
                client_name,
                elapsed_ms,
                exc,
            )
    return None, None, None, attempts


# -- Stand-alone entry point ---------------------------------------------------

if __name__ == "__main__":
    import asyncio  # noqa: F811
    import logging  # noqa: F811
    from utils.logger import set_stage_logger, setup_logging

    setup_logging()
    set_stage_logger("step4_full_text_retrieval")

    from models.paper import Paper  # noqa: F811
    from utils.intermediate_io import STEP3_FILE, STEP4_FILE, load_model_list, save_json

    async def _main() -> None:
        logger.info("[Step 4] START | Full-Text Retrieval")
        papers = load_model_list(STEP3_FILE, Paper)
        total = len(papers)
        papers = await FullTextRetriever().retrieve(papers)
        save_json(papers, STEP4_FILE)
        logger.info("Raw full-text retrieved for %d / %d papers.", len(papers), total)
        logger.info(
            "[Step 4] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
            total,
            len(papers),
            STEP4_FILE,
        )

    asyncio.run(_main())
