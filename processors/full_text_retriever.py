"""Step 3 – Full-Text Retrieval.

For every filtered paper, try all nine API clients in priority order and
store the first successful retrieval as a raw :class:`~models.paper.FullText`
object (PDF base-64, XML, HTML, or plain text).

Text extraction and format conversion happen in Step 4
(:mod:`processors.text_extractor`).
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import time as _time
from typing import List, Optional, Tuple

from models.paper import FullText, Paper
from api_clients import (
    COREClient,
    ElsevierClient,
    EuropePMCClient,
    PMCClient,
    SemanticScholarClient,
    UnpaywallClient,
)

logger = logging.getLogger(__name__)


class FullTextRetriever:
    """Step 3: attempt to fetch raw full-text for each paper from all sources."""

    # Priority order: open-access XML sources first, then PDF sources
    _CLIENT_ORDER = [
        ElsevierClient,
        
        EuropePMCClient,
        PMCClient,
        
        SemanticScholarClient,
        UnpaywallClient,
        COREClient
    ]

    async def retrieve(self, papers: List[Paper]) -> List[Paper]:
        """
        For each paper in *papers*, query every API client until one returns
        a non-empty :class:`FullText`.  The raw content (PDF, XML, HTML, or
        plain text) is stored in ``paper.full_text`` for later extraction.

        Papers for which no full text could be retrieved are returned with
        ``paper.full_text = None``; they will receive an abstract fallback in
        Step 4.
        """
        async with contextlib.AsyncExitStack() as stack:
            all_clients = [
                await stack.enter_async_context(cls())
                for cls in self._CLIENT_ORDER
            ]

            tasks = [
                _fetch_first_available(all_clients, paper) for paper in papers
            ]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        found = 0
        for paper, result in zip(papers, raw_results):
            if isinstance(result, tuple):
                ft, client_name, elapsed_ms = result
                if ft is not None:
                    paper.full_text = ft
                    paper.ft_retrieved_by = client_name
                    paper.ft_response_time_ms = elapsed_ms
                    found += 1
            elif isinstance(result, Exception):
                logger.warning(
                    "Full-text retrieval error for '%s': %s",
                    paper.title[:60],
                    result,
                )

        logger.info(
            "Step 3 – Full-text retrieved for %d / %d papers.",
            found,
            len(papers),
        )
        return papers


# Maps the class name suffix to a short source label used in the Paper model
_CLIENT_LABELS = {
    "EuropePMCClient":      "europe_pmc",
    "PMCClient":            "pmc",
    "ElsevierClient":       "elsevier",
    "SemanticScholarClient": "semantic_scholar",
    "UnpaywallClient":      "unpaywall",
    "COREClient":           "core",
}


async def _fetch_first_available(
    clients: list, paper: Paper
) -> Tuple[Optional[FullText], Optional[str], Optional[float]]:
    """Try each client in sequence; return (FullText, client_label, elapsed_ms)."""
    for client in clients:
        client_name = type(client).__name__
        t0 = _time.monotonic()
        try:
            ft = await client.fetch_full_text(paper)  # type: ignore[attr-defined]
            elapsed_ms = round((_time.monotonic() - t0) * 1000, 1)
            if ft is not None and ft.content.strip():
                label = _CLIENT_LABELS.get(client_name, client_name)
                return ft, label, elapsed_ms
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = round((_time.monotonic() - t0) * 1000, 1)
            logger.debug(
                "Full-text probe failed for '%s' via %s (%.0f ms): %s",
                paper.title[:60],
                client_name,
                elapsed_ms,
                exc,
            )
    return None, None, None


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio  # noqa: F811
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import STEP3_FILE, STEP4_FILE, load_model_list, save_json
    from models.paper import Paper  # noqa: F811

    async def _main() -> None:
        papers = load_model_list(STEP3_FILE, Paper)
        papers = await FullTextRetriever().retrieve(papers)
        save_json(papers, STEP4_FILE)
        fetched = sum(1 for p in papers if p.full_text)
        print(f"Full text retrieved for {fetched} / {len(papers)} papers.")
        print(f"Saved → intermediate_outputs/{STEP4_FILE}")

    asyncio.run(_main())
