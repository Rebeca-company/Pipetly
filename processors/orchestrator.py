"""Multi-Source Paper Search Orchestrator.

Convenience wrapper that coordinates the four modular pipeline steps:

1. :class:`~processors.paper_searcher.PaperSearcher`   – search all APIs for metadata
2. :class:`~processors.metadata_filter.MetadataFilter` – dedup + DOI filter
3. :class:`~processors.full_text_retriever.FullTextRetriever` – raw full-text fetch
4. :class:`~processors.text_extractor.TextExtractor`   – convert to clean plain text

Use this class when you want a single entry point that runs all four steps
end-to-end, or call each step class directly for fine-grained control.
"""
from __future__ import annotations

import logging
from typing import List

from models.paper import Paper
from models.query import ExpandedQuery
from .paper_searcher import PaperSearcher
from .metadata_filter import MetadataFilter
from .full_text_retriever import FullTextRetriever
from .text_extractor import TextExtractor

logger = logging.getLogger(__name__)


class MultiSourceOrchestrator:
    """Run all four paper-search pipeline steps and return papers with clean text."""

    async def fetch_papers(self, expanded_query: ExpandedQuery) -> List[Paper]:
        """
        Execute the four-step paper search pipeline:

        1. **Search** – fan out queries across all API clients.
        2. **Filter** – deduplicate and require a DOI.
        3. **Retrieve** – fetch raw full-text (PDF / XML / HTML / plain).
        4. **Extract** – convert to normalised plain text; abstract fallback.

        Returns papers ready for protocol extraction.
        """
        # Step 1 – Paper and Metadata Search
        papers = await PaperSearcher().search(expanded_query)

        # Step 2 – Metadata Filtering (dedup + DOI)
        papers = MetadataFilter().run(papers)
        if not papers:
            logger.warning("No papers with a DOI found after metadata filtering.")
            return []

        # Step 3 – Full-Text Retrieval
        papers = await FullTextRetriever().retrieve(papers)

        # Step 4 – Text Extraction (PDF / XML / HTML → plain text)
        papers = TextExtractor().extract_all(papers)

        return papers


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import (
        STEP1_FILE,
        STEP5_FILE,
        load_model,
        save_json,
    )
    from models.query import ExpandedQuery

    async def _main() -> None:
        expanded = load_model(STEP1_FILE, ExpandedQuery)
        orchestrator = MultiSourceOrchestrator()
        papers = await orchestrator.fetch_papers(expanded)
        save_json(papers, STEP5_FILE)
        print(f"Pipeline produced {len(papers)} papers with clean text.")
        print(f"Saved → intermediate_outputs/{STEP5_FILE}")

    asyncio.run(_main())

