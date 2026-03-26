"""Step 3 – Full-Text Retrieval.

For every filtered paper, try all configured API clients in priority order and
store the first successful retrieval as a raw :class:`~models.paper.FullText`
object (PDF base-64, XML, HTML, or plain text).

Text extraction and format conversion happen in Step 4
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
    COREClient,
    ElsevierClient,
    EuropePMCClient,
    OpenAlexClient,
    PMCClient,
    SemanticScholarClient,
    UnpaywallClient,
)
from models.paper import FullText, Paper

logger = logging.getLogger(__name__)


class FullTextRetriever:
    """Step 3: attempt to fetch raw full-text for each paper from all sources."""

    # Priority order: open-access XML sources first, then PDF sources
    _CLIENT_ORDER = [
        ElsevierClient,
        EuropePMCClient,
        PMCClient,
        OpenAlexClient,
        SemanticScholarClient,
        UnpaywallClient,
        COREClient,
    ]

    async def retrieve(self, papers: List[Paper]) -> List[Paper]:
        """
        For each paper in *papers*, query every API client until one returns
        a non-empty :class:`FullText`. The raw content (PDF, XML, HTML, or
        plain text) is stored in ``paper.full_text`` for later extraction.

        Returns only papers for which full text could be retrieved.
        """
        async with contextlib.AsyncExitStack() as stack:
            all_clients = [await stack.enter_async_context(cls()) for cls in self._CLIENT_ORDER]

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

            tasks = [_fetch_first_available(all_clients, paper) for paper in canonical_papers]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        found = 0
        for key, paper, result in zip(canonical_keys, canonical_papers, raw_results):
            target_group = key_to_papers.get(key, [paper])
            if isinstance(result, tuple):
                ft, client_name, elapsed_ms = result
                if ft is not None:
                    for target in target_group:
                        target.full_text = ft
                        target.ft_retrieved_by = client_name
                        target.ft_response_time_ms = elapsed_ms
                    found += len(target_group)
            elif isinstance(result, Exception):
                logger.warning(
                    "Full-text retrieval error for '%s': %s",
                    paper.title[:60],
                    result,
                )

        papers_with_full_text = [
            p for p in papers if p.full_text is not None and p.full_text.content.strip()
        ]
        logger.info(
            "Step 3 – Full-text retrieved for %d / %d papers. Returning %d papers with full text.",
            found,
            len(papers),
            len(papers_with_full_text),
        )
        return papers_with_full_text


# Maps the class name suffix to a short source label used in the Paper model
_CLIENT_LABELS = {
    "EuropePMCClient": "europe_pmc",
    "PMCClient": "pmc",
    "ElsevierClient": "elsevier",
    "OpenAlexClient": "openalex",
    "SemanticScholarClient": "semantic_scholar",
    "UnpaywallClient": "unpaywall",
    "COREClient": "core",
}

_PMCID_RE = re.compile(r"PMC\d+", re.IGNORECASE)


def _paper_dedup_key(paper: Paper) -> str:
    """Return a stable key for deduplicating fetch requests."""
    if paper.doi:
        return f"doi:{paper.doi.strip().lower()}"
    if paper.url:
        match = _PMCID_RE.search(paper.url)
        if match:
            return f"pmcid:{match.group(0).upper()}"
    return f"unique:{id(paper)}"


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


# -- Stand-alone entry point ---------------------------------------------------

if __name__ == "__main__":
    import asyncio  # noqa: F811
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )

    from models.paper import Paper  # noqa: F811
    from utils.intermediate_io import STEP3_FILE, STEP4_FILE, load_model_list, save_json

    async def _main() -> None:
        papers = load_model_list(STEP3_FILE, Paper)
        total = len(papers)
        papers = await FullTextRetriever().retrieve(papers)
        save_json(papers, STEP4_FILE)
        print(f"Full text retrieved for {len(papers)} / {total} papers.")
        print(f"Saved -> intermediate_outputs/{STEP4_FILE}")

    asyncio.run(_main())
