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
8. Protocol Scoring        – re-score extracted protocols with score > 60.
9. Final Formatting & Output – package Top 3 protocols and write Markdown report.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from config import get_settings
from utils.logger import set_stage_logger, setup_logging
from utils.telemetry import calculate_pipeline_costs, calculate_pipeline_time_summary
from processors import (
    FullTextFilter,
    FullTextRetriever,
    MetadataFilter,
    PaperSearcher,
    ProtocolExtractor,
    ProtocolScorer,
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
    TEST_LLM_TOKEN_USAGE_FILE,
    TEST_LLM_TIME_USAGE_FILE,
    save_json,
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
    set_stage_logger("step1_query_expansion")
    logger.info("[Step 1] START | Query Expansion")
    expander = QueryExpander()
    expanded = await expander.expand(user_prompt)
    step1_token_events = expander.get_llm_token_events()
    logger.info("Intent  : %s", expanded.intent)
    logger.info("Queries : %s", expanded.queries)

    save_json(expanded, STEP1_FILE)
    logger.info(
        "[Step 1] DONE | intent_generated=true concept_queries=%d | Output: intermediate_outputs/%s",
        len(expanded.queries),
        STEP1_FILE,
    )

    # ── Step 2: Paper and Metadata Search ────────────────────────────────────
    set_stage_logger("step2_paper_search")
    logger.info("[Step 2] START | Paper and Metadata Search")
    search_result = await PaperSearcher().search(expanded)
    save_json(search_result, STEP2_FILE)
    logger.info(
        "[Step 2] DONE | raw_records=%d | Output: intermediate_outputs/%s",
        len(search_result.papers),
        STEP2_FILE,
    )

    # ── Step 3: Metadata Filtering (dedup + DOI) ─────────────────────────────
    set_stage_logger("step3_metadata_filter")
    logger.info("[Step 3] START | Metadata Filtering")
    doi_filtered = MetadataFilter().run(search_result.papers)
    logger.info("%d unique papers with DOI after filtering.", len(doi_filtered))
    save_json(doi_filtered, STEP3_FILE)
    logger.info(
        "[Step 3] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(search_result.papers),
        len(doi_filtered),
        STEP3_FILE,
    )

    if not doi_filtered:
        logger.warning("No papers with a DOI found. Try a broader query.")
        raise RuntimeError("No papers with a DOI found. Adjust your query or API keys.")

    # ── Step 4: Full-Text Retrieval ───────────────────────────────────────────
    set_stage_logger("step4_full_text_retrieval")
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
    set_stage_logger("step5_text_extraction")
    logger.info("[Step 5] START | Text Extraction")
    extracted_papers = TextExtractor().extract_all(ft_papers)
    with_text = sum(1 for p in extracted_papers if p.full_text)
    logger.info(
        "%d / %d papers have clean plain text.", with_text, len(extracted_papers)
    )
    save_json(extracted_papers, STEP5_FILE)
    logger.info(
        "[Step 5] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(ft_papers),
        with_text,
        STEP5_FILE,
    )

    # ── Step 6: Post-Extraction Filter (full text length bounds) ─────────────
    set_stage_logger("step6_post_extraction_filter")
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

    # ── Step 7: Recursive Protocol Extraction (7.1-7.4) ──────────────────────
    set_stage_logger("step7_protocol_extraction")
    logger.info("[Step 7] START | Recursive Protocol Extraction")
    extractor = ProtocolExtractor(max_depth=_s.max_citation_depth)
    protocols = await extractor.extract_all(filtered, expanded.intent)
    step7_token_events = extractor.get_llm_token_events()

    logger.info(
        "Extracted %d protocol fragments (only score=0 and empty text are discarded).",
        len(protocols),
    )
    save_json(protocols, STEP7_FILE)
    logger.info(
        "[Step 7] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(filtered),
        len(protocols),
        STEP7_FILE,
    )
    if not protocols:
        raise RuntimeError("No protocols could be extracted from the filtered papers.")

    # ── Step 8: Protocol Scoring ─────────────────────────────────────────────
    set_stage_logger("step8_protocol_scoring")
    logger.info("[Step 8] START | Protocol Scoring")
    scorer = ProtocolScorer()
    rescored_protocols = await scorer.score_all(protocols, expanded.intent)
    step8_token_events = scorer.get_llm_token_events()
    save_json(rescored_protocols, STEP8_FILE)
    logger.info("Re-scored %d protocols from Step 7.", len(rescored_protocols))
    logger.info(
        "[Step 8] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
        len(protocols),
        len(rescored_protocols),
        STEP8_FILE,
    )

    # ── Step 9: Final Formatting & Output ────────────────────────────────────
    set_stage_logger("step9_final_formatting")
    logger.info("[Step 9] START | Final Formatting and Output")
    formatter = ProtocolFormatter()
    top_protocols = await formatter.format_top_protocols(rescored_protocols)
    logger.info("Top %d protocols selected.", len(top_protocols))
    for item in top_protocols:
        logger.info("  [%.2f] %s", item.score, item.protocol.source_title)

    output_path = await formatter.format_and_write(
        rescored_protocols,
        expanded.intent,
        _s.output_dir,
    )
    step9_token_events = formatter.get_llm_token_events()

    raw_token_events = [
        *[{"component": "query_expander", **event} for event in step1_token_events],
        *[{"component": "protocol_extractor", **event} for event in step7_token_events],
        *[{"component": "protocol_scorer", **event} for event in step8_token_events],
        *[{"component": "protocol_formatter", **event} for event in step9_token_events],
    ]

    token_events, total_summary = await calculate_pipeline_costs(
        raw_events=raw_token_events,
        model_id=_s.llm_model_general,
    )

    logger.info("Pipeline tokens:")
    logger.info("  Input  : %d", total_summary["total_input_tokens"])
    logger.info("  Output : %d", total_summary["total_output_tokens"])
    logger.info("Estimated pipeline cost:")
    logger.info("  $%.6f (input) + $%.6f (output) = $%.6f total", 
                total_summary["total_input_cost_usd"], 
                total_summary["total_output_cost_usd"], 
                total_summary["total_pipeline_cost_usd"])

    save_json(
        {
            "token_events": token_events,
            "total_summary": total_summary,
        },
        TEST_LLM_TOKEN_USAGE_FILE,
    )
    logger.info(
        "[Testing] Token telemetry saved | calls=%d total_tokens=%d | Output: intermediate_outputs/%s",
        len(token_events),
        total_summary["total_tokens"],
        TEST_LLM_TOKEN_USAGE_FILE,
    )

    # ── Time telemetry ──────────────────────────────────────────────────────
    time_events, time_summary = calculate_pipeline_time_summary(
        raw_events=token_events,
        model_id=_s.llm_model_general,
    )
    save_json(
        {
            "token_events": time_events,
            "total_summary": time_summary,
        },
        TEST_LLM_TIME_USAGE_FILE,
    )
    logger.info(
        "[Testing] Time telemetry saved | calls=%d total_gen_ms=%.0f | Output: intermediate_outputs/%s",
        len(time_events),
        time_summary["total_generation_time_ms"],
        TEST_LLM_TIME_USAGE_FILE,
    )

    logger.info(
        "[Step 9] DONE | candidates=%d top_k=%d | Output: %s",
        len(rescored_protocols),
        len(top_protocols),
        output_path,
    )
    logger.info("[Pipeline] DONE")
    set_stage_logger(None)
    return output_path


def main() -> None:
    setup_logging()
    if len(sys.argv) < 2:
        print('Usage: python main.py "<your research question>"')
        sys.exit(1)
    prompt = " ".join(sys.argv[1:])
    output = asyncio.run(run_pipeline(prompt))
    print(f"[Pipeline] DONE | Output: {output}")


if __name__ == "__main__":
    main()
