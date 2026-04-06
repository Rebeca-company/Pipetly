"""Multi-Source Paper Search Orchestrator.

Coordinates global pipeline Steps 2 through 6:

2. :class:`~processors.paper_searcher.PaperSearcher`   - search all APIs for metadata
3. :class:`~processors.metadata_filter.MetadataFilter` - dedup + DOI filter
4. :class:`~processors.full_text_retriever.FullTextRetriever` - raw full-text fetch
5. :class:`~processors.text_extractor.TextExtractor`   - convert to clean plain text
6. :class:`~processors.full_text_filter.FullTextFilter` - keep papers within accepted text-length bounds

Use this class when you want a single entry point that runs all steps
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
from .full_text_filter import FullTextFilter
from utils.intermediate_io import (
    STEP2_FILE,
    STEP3_FILE,
    STEP4_FILE,
    STEP5_FILE,
    STEP6_FILE,
    save_json,
)

logger = logging.getLogger(__name__)


class MultiSourceOrchestrator:
    """Run the paper-search pipeline and return papers with clean, filtered text."""

    async def fetch_papers(
        self,
        expanded_query: ExpandedQuery,
        save_intermediate: bool = True,
    ) -> List[Paper]:
        """
        Execute the paper search pipeline:

        2. **Search** - fan out queries across all API clients.
        3. **Filter** - deduplicate and require a DOI.
        4. **Retrieve** - fetch raw full-text (PDF / XML / HTML / plain).
        5. **Extract** - convert to normalised plain text.
        6. **Post-filter** - keep only papers with usable full text length.

        Returns papers ready for protocol extraction (post-filtered).
        """
        logger.info("Orchestrator start - running Steps 2 to 6.")
        # Step 2 - Paper and metadata search
        papers = await PaperSearcher().search(expanded_query)
        if save_intermediate:
            save_json(papers, STEP2_FILE)

        # Step 3 - Metadata filtering (dedup + DOI)
        papers = MetadataFilter().run(papers)
        if not papers:
            logger.warning("No papers with a DOI found after metadata filtering.")
            return []
        if save_intermediate:
            save_json(papers, STEP3_FILE)

        # Step 4 - Full-text retrieval
        papers = await FullTextRetriever().retrieve(papers)
        if save_intermediate:
            save_json(papers, STEP4_FILE)

        # Step 5 - Text extraction (PDF/XML/HTML to plain text)
        papers = TextExtractor().extract_all(papers)
        if save_intermediate:
            save_json(papers, STEP5_FILE)

        # Step 6 - Full-text length filter
        papers = FullTextFilter().run(papers)
        if save_intermediate:
            save_json(papers, STEP6_FILE)

        logger.info("Orchestrator complete - returning %d papers after Step 6.", len(papers))
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
        load_model,
    )
    from models.query import ExpandedQuery

    async def _main() -> None:
        print("[Orchestrator] START | Steps 2-6")
        expanded = load_model(STEP1_FILE, ExpandedQuery)
        orchestrator = MultiSourceOrchestrator()
        papers = await orchestrator.fetch_papers(expanded, save_intermediate=True)
        print(f"Pipeline produced {len(papers)} papers after full-text filter.")
        print(
            f"[Orchestrator] DONE | output={len(papers)} | Outputs: "
            f"intermediate_outputs/{STEP2_FILE}, "
            f"intermediate_outputs/{STEP3_FILE}, "
            f"intermediate_outputs/{STEP4_FILE}, "
            f"intermediate_outputs/{STEP5_FILE}, "
            f"intermediate_outputs/{STEP6_FILE}"
        )

    asyncio.run(_main())

