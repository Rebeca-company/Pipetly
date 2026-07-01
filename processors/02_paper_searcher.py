"""Step 2 – Paper and Metadata Search.

Fan out all keyword queries across every configured API client and collect
raw paper metadata records.  Duplicates and papers without DOIs are kept at
this stage; they are cleaned up in Step 3 (MetadataFilter).
"""

from __future__ import annotations

import asyncio
import logging
import time as _time
from typing import List

from config import get_settings
from models.paper import Paper, SearchResult, SearchTelemetry
from models.query import ExpandedQuery
from api_clients import (
    CrossRefClient,
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    ScopusClient,
    SemanticScholarClient,
)

logger = logging.getLogger(__name__)
_s = get_settings()


# Clients that support search (Unpaywall has no search endpoint)
class PaperSearcher:
    """Step 2: fan-out search over all API clients and return raw paper metadata."""

    async def search(self, expanded_query: ExpandedQuery) -> SearchResult:
        """
        Execute **every** keyword query against **every** configured search API
        concurrently so that the notebook can measure per-API performance
        without any pre-filtering.

        Papers may be duplicated across sources;
        deduplication is handled in
        :class:`processors.metadata_filter.MetadataFilter` (Step 3).
        """
        all_papers: list[Paper] = []

        async with (
            EuropePMCClient() as epmc,
            SemanticScholarClient() as s2,
            ElsevierClient() as els,
            CrossRefClient() as cr,
            OpenAlexClient() as oa,
            ScopusClient() as scopus,
        ):
            ALL_APIS = [
                (epmc, "europe_pmc"),
                (s2, "semantic_scholar"),
                (els, "elsevier"),
                (cr, "crossref"),
                (oa, "openalex"),
                (scopus, "scopus"),
            ]

            # ── Timed wrapper ─────────────────────────────────────────────
            async def _timed_search(coro, client_name: str, query: str):
                """Run one search coroutine, returning (client_name, query, papers, elapsed_ms, is_error)."""
                t0 = _time.monotonic()
                try:
                    papers = await coro
                    elapsed_ms = (_time.monotonic() - t0) * 1000
                    return client_name, query, papers, round(elapsed_ms, 1), False
                except Exception as exc:  # noqa: BLE001
                    elapsed_ms = (_time.monotonic() - t0) * 1000
                    logger.warning("Search error [%s]: %s", client_name, exc)
                    return client_name, query, [], round(elapsed_ms, 1), True

            tasks: list = []

            for q in expanded_query.queries:
                for client, api_label in ALL_APIS:
                    tasks.append(
                        _timed_search(client.search(q, _s.max_papers_per_source), api_label, q)
                    )

            # --- Concurrent execution (exceptions handled inside _timed_search) ---
            results = await asyncio.gather(*tasks)

            telemetry = []
            for client_name, query, papers, elapsed_ms, is_err in results:
                for paper in papers:
                    paper.response_time_ms = elapsed_ms
                    paper.is_error = is_err
                all_papers.extend(papers)
                
                telemetry.append(SearchTelemetry(
                    query=query,
                    client=client_name,
                    elapsed_ms=elapsed_ms,
                    is_error=is_err,
                    results_count=len(papers),
                ))

        logger.info(
            "Collected %d raw paper records from %d search tasks across %d concept queries.",
            len(all_papers),
            len(tasks),
            len(expanded_query.queries),
        )
        return SearchResult(papers=all_papers, telemetry=telemetry)


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811
    from utils.logger import set_stage_logger, setup_logging

    setup_logging()
    set_stage_logger("step2_paper_search")

    from utils.intermediate_io import STEP1_FILE, STEP2_FILE, load_model, save_json
    from models.query import ExpandedQuery

    async def _main() -> None:
        logger.info("[Step 2] START | Paper and Metadata Search")
        expanded = load_model(STEP1_FILE, ExpandedQuery)
        search_result = await PaperSearcher().search(expanded)
        save_json(search_result, STEP2_FILE)
        logger.info("Collected %d raw papers.", len(search_result.papers))
        logger.info(
            "[Step 2] DONE | raw_records=%d | Output: intermediate_outputs/%s",
            len(search_result.papers),
            STEP2_FILE,
        )

    asyncio.run(_main())
