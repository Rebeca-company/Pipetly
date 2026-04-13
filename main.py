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
6. Post-Extraction Filter  – keep only papers with full text length in accepted range.
7. Protocol Extraction     – LLM extraction of protocol fragments + inherited refs.
8. Solve References        – iterative inherited-reference resolution (max depth 3).
9. Protocol Scoring        – re-score resolved protocols with score > 60.
10. Final Formatting & Output – package Top 3 protocols and write Markdown report.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from config import get_settings
from models.protocol import ExtractedProtocol
from processors import (
    FullTextFilter,
    FullTextRetriever,
    MetadataFilter,
    PaperSearcher,
    ProtocolExtractor,
    ProtocolScorer,
    ReferenceResolver,
    ProtocolFormatter,
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
    STEP8_FILE,
    STEP9_FILE,
    save_json,
)

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

    logger.info("[Pipeline] START")
    logger.info("User prompt: %s", user_prompt)

    # ── Step 1: Query Expansion ───────────────────────────────────────────────
    logger.info("[Step 1] START | Query Expansion")
    expander = QueryExpander()
    expanded = await expander.expand(user_prompt)
    logger.info("Intent  : %s", expanded.intent)
    logger.info("Queries : %s", expanded.concept_strings)
    
    save_json(expanded, STEP1_FILE)
    logger.info(
        "[Step 1] DONE | intent_generated=true concept_queries=%d | Output: intermediate_outputs/%s",
        len(expanded.concept_strings),
        STEP1_FILE,
    )

    # ── Step 2: Paper and Metadata Search ────────────────────────────────────
    logger.info("[Step 2] START | Paper and Metadata Search")
    raw_papers = await PaperSearcher().search(expanded)
    logger.info("Collected %d raw paper records from all API sources.", len(raw_papers))
    save_json(raw_papers, STEP2_FILE)
    logger.info(
        "[Step 2] DONE | raw_records=%d | Output: intermediate_outputs/%s",
        len(raw_papers),
        STEP2_FILE,
    )

    # ── Step 3: Metadata Filtering (dedup + DOI) ─────────────────────────────
    logger.info("[Step 3] START | Metadata Filtering")
    doi_filtered = MetadataFilter().run(raw_papers)
    logger.info("%d unique papers with DOI after filtering.", len(doi_filtered))
    save_json(doi_filtered, STEP3_FILE)
    logger.info(
        "[Step 3] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(raw_papers),
        len(doi_filtered),
        STEP3_FILE,
    )

    if not doi_filtered:
        logger.warning("No papers with a DOI found. Try a broader query.")
        raise RuntimeError("No papers with a DOI found. Adjust your query or API keys.")

    # ── Step 4: Full-Text Retrieval ───────────────────────────────────────────
    logger.info("[Step 4] START | Full-Text Retrieval")
    ft_papers = await FullTextRetriever().retrieve(doi_filtered)
    logger.info(
        "Raw full-text retrieved for %d / %d papers.",
        len(ft_papers),
        len(doi_filtered),
    )
    save_json(ft_papers, STEP4_FILE)
    logger.info(
        "[Step 4] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(doi_filtered),
        len(ft_papers),
        STEP4_FILE,
    )

    # ── Step 5: Text Extraction (PDF / XML / HTML → plain text) ──────────────
    logger.info("[Step 5] START | Text Extraction")
    extracted_papers = TextExtractor().extract_all(ft_papers)
    with_text = sum(1 for p in extracted_papers if p.full_text)
    logger.info("%d / %d papers have clean plain text.", with_text, len(extracted_papers))
    save_json(extracted_papers, STEP5_FILE)
    logger.info(
        "[Step 5] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(ft_papers),
        with_text,
        STEP5_FILE,
    )

    # ── Step 6: Post-Extraction Filter (full text length bounds) ─────────────
    logger.info("[Step 6] START | Post-Extraction Filter")
    filtered = FullTextFilter().run(extracted_papers)
    save_json(filtered, STEP6_FILE)
    logger.info("%d papers passed post-extraction filter.", len(filtered))
    logger.info(
        "[Step 6] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(extracted_papers),
        len(filtered),
        STEP6_FILE,
    )

    if not filtered:
        logger.warning("No papers passed the filter. Try a broader query.")
        raise RuntimeError("No eligible papers found. Adjust your query or API keys.")

    # ── Step 7: Protocol Extraction ───────────────────────────────────────────
    logger.info("[Step 7] START | Protocol Extraction")
    extractor = ProtocolExtractor()
    protocols = await extractor.extract_all(filtered, expanded.intent)

    logger.info("Extracted %d protocol fragments (only score=0 and empty text are discarded).", len(protocols))
    save_json(protocols, STEP7_FILE)
    logger.info(
        "[Step 7] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(filtered),
        len(protocols),
        STEP7_FILE,
    )
    if not protocols:
        raise RuntimeError("No protocols could be extracted from the filtered papers.")

    # ── Step 8: Resolve Inherited References ─────────────────────────────────
    logger.info("[Step 8] START | Solve Inherited References")
    logger.info("Running inherited-reference resolution with Step 8 score filter (>= 70).")
    resolver = ReferenceResolver(max_depth=3)
    resolved_protocols = await resolver.resolve_all(protocols)
    save_json(resolved_protocols, STEP8_FILE)
    logger.info(
        "[Step 8] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(protocols),
        len(resolved_protocols),
        STEP8_FILE,
    )

    # ── Step 9: Protocol Scoring (post-resolution) ───────────────────────────
    logger.info("[Step 9] START | Protocol Scoring")
    scorer = ProtocolScorer()
    rescored_protocols = await scorer.score_all(resolved_protocols, expanded.intent)
    save_json(rescored_protocols, STEP9_FILE)
    logger.info("Re-scored %d protocols from Step 8.", len(rescored_protocols))
    logger.info(
        "[Step 9] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(resolved_protocols),
        len(rescored_protocols),
        STEP9_FILE,
    )

    # ── Step 10: Final Formatting & Output ───────────────────────────────────
    logger.info("[Step 10] START | Final Formatting and Output")
    formatter = ProtocolFormatter()
    top_protocols = await formatter.format_top_protocols(rescored_protocols, expanded.intent)
    logger.info("Top %d protocols selected.", len(top_protocols))
    for item in top_protocols:
        logger.info("  [%.2f] %s", item.score, item.protocol.source_title)

    output_path = await formatter.format_and_write(
        rescored_protocols,
        expanded.intent,
        _s.output_dir,
    )
    logger.info(
        "[Step 10] DONE | candidates=%d top_k=%d | Output: %s",
        len(rescored_protocols),
        len(top_protocols),
        output_path,
    )
    logger.info("[Pipeline] DONE")
    return output_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<your research question>\"")
        sys.exit(1)
    prompt = " ".join(sys.argv[1:])
    output = asyncio.run(run_pipeline(prompt))
    print(f"[Pipeline] DONE | Output: {output}")


if __name__ == "__main__":
    main()
