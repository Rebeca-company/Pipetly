"""
Pipetly – Biomedical Protocol Extractor
========================================
Entry-point.  Run with::

    python main.py "protocol for CRISPR-Cas9 gene editing in human cell lines"

Or import and call :func:`run_pipeline` from your own code.
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
    MultiSourceOrchestrator,
    ProtocolExtractor,
    ProtocolScorer,
    QueryExpander,
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
    generated Markdown file.
    """

    # ── Step 1: Query Expansion ───────────────────────────────────────────────
    logger.info("=== Step 1/5 – Query Expansion ===")
    expander = QueryExpander()
    expanded = await expander.expand(user_prompt)
    logger.info("Intent  : %s", expanded.intent)
    logger.info("Keywords: %s", expanded.keyword_queries)
    logger.info("Semantic: %s", expanded.semantic_queries)

    # ── Step 2: Multi-Source Fetch ────────────────────────────────────────────
    logger.info("=== Step 2/5 – Multi-Source Orchestration ===")
    orchestrator = MultiSourceOrchestrator()
    raw_papers = await orchestrator.fetch_papers(expanded)
    logger.info("Fetched %d raw papers across all sources.", len(raw_papers))

    # ── Step 3: Filtering ─────────────────────────────────────────────────────
    logger.info("=== Step 3/5 – Strict Filtering Pipeline ===")
    pipeline = FilterPipeline()
    filtered = pipeline.run(raw_papers)
    logger.info("%d papers passed filters.", len(filtered))

    if not filtered:
        logger.warning("No papers passed the filter. Try a broader query.")
        raise RuntimeError("No eligible papers found. Adjust your query or API keys.")

    # ── Step 4: Protocol Extraction (with Citation Investigator) ──────────────
    logger.info("=== Step 4/5 – Recursive Protocol Extraction ===")
    extractor = ProtocolExtractor()
    protocols: list[ExtractedProtocol] = []
    for paper in filtered:
        logger.info("Extracting from: %s", paper.title[:80])
        proto = await extractor.extract(paper)
        if proto:
            protocols.append(proto)

    logger.info("Extracted %d protocols.", len(protocols))
    if not protocols:
        raise RuntimeError("No protocols could be extracted from the filtered papers.")

    # ── Step 5: Scoring & Output ──────────────────────────────────────────────
    logger.info("=== Step 5/5 – Scoring & Final Delivery ===")
    scorer = ProtocolScorer()
    scored = await scorer.score_all(protocols, expanded.intent)
    logger.info("Top %d protocols scored.", len(scored))
    for sp in scored:
        logger.info("  [%.2f] %s", sp.score, sp.protocol.protocol_name)

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
