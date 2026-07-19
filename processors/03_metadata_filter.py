"""Step 3 – Metadata Filtering.

Remove duplicate papers and entries that lack a DOI so that downstream
steps (full-text retrieval, protocol extraction) operate on a clean,
deduplicated set of uniquely identifiable records.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List

from models.paper import Paper

logger = logging.getLogger(__name__)

_DOI_PREFIX_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)


def _canonical_doi(doi: str) -> str:
    """Return a normalized DOI key suitable for deduplication."""
    normalized = _DOI_PREFIX_RE.sub("", doi.strip()).strip().lower()
    return normalized.rstrip("/.")


def _completeness(paper: Paper) -> int:
    """Return a metadata-completeness score (higher = more complete)."""
    score = 0
    if paper.doi:
        score += 1
    if paper.title:
        score += 1
    if paper.abstract:
        score += 3  # abstract is high-value
    if paper.authors:
        score += min(len(paper.authors), 10)
    if paper.year:
        score += 1
    if paper.url:
        score += 1
    return score


class MetadataFilter:
    """Step 3: deduplicate by DOI, keep the most complete record."""

    def run(self, papers: List[Paper]) -> List[Paper]:
        """
        Filter *papers* and return a deduplicated list of papers that all
        possess a canonical DOI.

        Rules applied in order:

        1. **DOI required** – papers that carry no DOI are discarded.
        2. **DOI deduplication** – papers sharing the same DOI
           (case-insensitive) are collapsed; the record with the highest
           metadata-completeness score is kept.
        """
        no_doi: int = 0
        invalid_doi: int = 0

        # ── Pass 1: DOI deduplication ─────────────────────────────────────
        doi_best: Dict[str, Paper] = {}
        for paper in papers:
            if not paper.doi:
                no_doi += 1
                logger.debug("No DOI – discarding '%s'", paper.title[:60])
                continue
            uid = _canonical_doi(paper.doi)
            if not uid:
                invalid_doi += 1
                logger.debug(
                    "Invalid DOI after normalization – discarding '%s'",
                    paper.title[:60],
                )
                continue
            if uid in doi_best:
                if _completeness(paper) > _completeness(doi_best[uid]):
                    logger.debug(
                        "DOI duplicate – keeping new from '%s' over existing from '%s' (DOI: %s)",
                        paper.source,
                        doi_best[uid].source,
                        paper.doi,
                    )
                    doi_best[uid] = paper
                else:
                    logger.debug(
                        "DOI duplicate – keeping existing from '%s' over new from '%s' (DOI: %s)",
                        doi_best[uid].source,
                        paper.source,
                        paper.doi,
                    )
            else:
                doi_best[uid] = paper

        doi_dupes = len(papers) - no_doi - invalid_doi - len(doi_best)

        accepted = list(doi_best.values())

        logger.info(
            "Metadata filtering: %d raw -> %d accepted "
            "(%d no-DOI discarded, %d invalid-DOI discarded, %d DOI-duplicates removed).",
            len(papers),
            len(accepted),
            no_doi,
            invalid_doi,
            doi_dupes,
        )
        return accepted


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811

    from utils.logger import setup_logging, set_stage_logger

    setup_logging()
    set_stage_logger("step3_metadata_filter")

    from utils.intermediate_io import STEP2_FILE, STEP3_FILE, load_model, save_json
    from models.paper import SearchResult  # noqa: F811

    def _main() -> None:
        search_result = load_model(STEP2_FILE, SearchResult)
        _papers = search_result.papers
        logger.info("[Step 3] START | Metadata Filtering")
        _filtered = MetadataFilter().run(_papers)
        save_json(_filtered, STEP3_FILE)
        logger.info("%d unique papers with DOI after filtering.", len(_filtered))
        logger.info(
            "[Step 3] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
            len(_papers),
            len(_filtered),
            STEP3_FILE,
        )

    _main()
