"""
Pipetly – Biomedical Protocol Extractor
========================================
Entry-point.  Run with::

    python main.py "protocol for CRISPR-Cas9 gene editing in human cell lines"

Or import and call :func:`run_pipeline` from your own code.

Pipeline overview
-----------------
1. Query Expansion        – expand the user prompt into structured search queries.
2. Paper & Metadata Search – fan out to all eight search API clients; collect raw records.
3. Metadata Filtering      – deduplicate and require a DOI.
4. Full-Text Retrieval     – fetch raw full-text (PDF / XML / HTML) from six sources.
5. Text Extraction         – convert to clean plain text; abstract fallback.
6. Post-Extraction Filter  – require full text and a detectable methods section.
7. Protocol Extraction     – LLM-based extraction of experimental protocols.
8. Scoring & Output        – rank protocols and write Markdown report.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from config import get_settings
from models.protocol import ExtractedProtocol
from processors import (
    FilterPipeline,
    FullTextRetriever,
    MetadataFilter,
    PaperSearcher,
    ProtocolExtractor,
    ProtocolScorer,
    QueryExpander,
    TextExtractor,
)
from utils.intermediate_io import (
    STEP1_FILE,
    STEP2_FILE,
    STEP3_FILE,
    STEP4_FILE,
    STEP5_FILE,
    STEP6_FILE,
    STEP7_FILE,
    save_json,
)
from utils.output_formatter import write_markdown_output

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipetly")
_s = get_settings()


async def run_pipeline(user_prompt: str) -> Path:
    """
    Execute the full Pipetly pipeline and return the path of the
    generated Markdown report.
    """

    # ── Step 1: Query Expansion ───────────────────────────────────────────────
    logger.info("=== Step 1/8 – Query Expansion ===")
    expander = QueryExpander()
    expanded = await expander.expand(user_prompt)
    logger.info("Intent  : %s", expanded.intent)
    logger.info("Queries : %s", expanded.queries)
    
    save_json(expanded, STEP1_FILE)

    # ── Step 2: Paper and Metadata Search ────────────────────────────────────
    logger.info("=== Step 2/8 – Paper and Metadata Search ===")
    raw_papers = await PaperSearcher().search(expanded)
    logger.info("Collected %d raw paper records from all API sources.", len(raw_papers))
    save_json(raw_papers, STEP2_FILE)

    # ── Step 3: Metadata Filtering (dedup + DOI) ─────────────────────────────
    logger.info("=== Step 3/8 – Metadata Filtering ===")
    doi_filtered = MetadataFilter().run(raw_papers)
    logger.info("%d unique papers with DOI after filtering.", len(doi_filtered))
    save_json(doi_filtered, STEP3_FILE)

    if not doi_filtered:
        logger.warning("No papers with a DOI found. Try a broader query.")
        raise RuntimeError("No papers with a DOI found. Adjust your query or API keys.")

    # ── Step 4: Full-Text Retrieval ───────────────────────────────────────────
    logger.info("=== Step 4/8 – Full-Text Retrieval ===")
    ft_papers = await FullTextRetriever().retrieve(doi_filtered)
    fetched = sum(1 for p in ft_papers if p.full_text)
    logger.info("Raw full-text retrieved for %d / %d papers.", fetched, len(ft_papers))
    save_json(ft_papers, STEP4_FILE)

    # ── Step 5: Text Extraction (PDF / XML / HTML → plain text) ──────────────
    logger.info("=== Step 5/8 – Text Extraction ===")
    extracted_papers = TextExtractor().extract_all(ft_papers)
    with_text = sum(1 for p in extracted_papers if p.full_text)
    logger.info("%d / %d papers have clean plain text.", with_text, len(extracted_papers))
    save_json(extracted_papers, STEP5_FILE)

    # ── Step 6: Post-Extraction Filter (full text + methods section) ──────────
    logger.info("=== Step 6/8 – Post-Extraction Filter ===")
    filtered = FilterPipeline().run(extracted_papers)
    logger.info("%d papers passed post-extraction filter.", len(filtered))

    if not filtered:
        logger.warning("No papers passed the filter. Try a broader query.")
        raise RuntimeError("No eligible papers found. Adjust your query or API keys.")

    # ── Step 7: Protocol Extraction ───────────────────────────────────────────
    logger.info("=== Step 7/8 – Protocol Extraction ===")
    extractor = ProtocolExtractor()
    protocols: list[ExtractedProtocol] = []
    for paper in filtered:
        logger.info("Extracting from: %s", paper.title[:80])
        proto = await extractor.extract(paper)
        if proto:
            protocols.append(proto)

    logger.info("Extracted %d protocols.", len(protocols))
    save_json(protocols, STEP6_FILE)
    if not protocols:
        raise RuntimeError("No protocols could be extracted from the filtered papers.")

    # ── Step 8: Scoring & Output ──────────────────────────────────────────────
    logger.info("=== Step 8/8 – Scoring & Final Delivery ===")
    scorer = ProtocolScorer()
    scored = await scorer.score_all(protocols, expanded.intent)
    logger.info("Top %d protocols scored.", len(scored))
    for sp in scored:
        logger.info("  [%.2f] %s", sp.score, sp.protocol.protocol_name)
    save_json(scored, STEP7_FILE)

    output_path = write_markdown_output(scored, expanded.intent, _s.output_dir)
    logger.info("Output written to: %s", output_path)
    return output_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<your research question>\"")
        sys.exit(1)
    prompt = " ".join(sys.argv[1:])
    output = asyncio.run(run_pipeline(prompt))
    print(f"\nDone! Protocol report saved to: {output}")


if __name__ == "__main__":
    main()
