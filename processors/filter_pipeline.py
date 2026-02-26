"""Module 3 – Strict Filtering Pipeline.

Removes duplicates, discards papers without DOI or full text, and enforces
a Regex-based methodology section check.
"""
from __future__ import annotations

import logging
import re
from typing import List

from models.paper import Paper

logger = logging.getLogger(__name__)

# Regex pattern that must match at least one methodology-like section header
_METHODS_RE = re.compile(
    r"(?imx)"                           # flags first, then the pattern
    r"("
    r"materials?\s+and\s+methods?"
    r"|experimental\s+section"
    r"|methods?\s+and\s+materials?"
    r"|^methods?\s*$"
    r"|procedures?\s+and\s+methods?"
    r"|experimental\s+procedures?"
    r"|protocol"
    r")",
)


class FilterPipeline:
    """Stateless filter – call :py:meth:`run` with a list of raw papers."""

    def run(self, papers: List[Paper]) -> List[Paper]:
        seen_ids: set[str] = set()
        accepted: list[Paper] = []
        discarded_dup = discarded_doi = discarded_ft = discarded_methods = 0

        for paper in papers:
            uid = paper.unique_id()

            # 1. Deduplication
            if uid in seen_ids:
                discarded_dup += 1
                continue
            seen_ids.add(uid)

            # 2. Must have a DOI
            if not paper.doi:
                discarded_doi += 1
                logger.debug("No DOI – discarding '%s'", paper.title[:60])
                continue

            # 3. Must have full text
            if not paper.full_text or not paper.full_text.content.strip():
                discarded_ft += 1
                logger.debug("No full text – discarding '%s'", paper.title[:60])
                continue

            # 4. Methods-section check (waived for abstract-only content)
            if not paper.full_text.is_abstract_only:
                if not _METHODS_RE.search(paper.full_text.content):
                    discarded_methods += 1
                    logger.debug(
                        "No methods section – discarding '%s'", paper.title[:60]
                    )
                    continue

            accepted.append(paper)

        logger.info(
            "Filter results: %d accepted | %d duplicates | %d no-DOI | "
            "%d no-full-text | %d no-methods",
            len(accepted),
            discarded_dup,
            discarded_doi,
            discarded_ft,
            discarded_methods,
        )
        return accepted


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import (  # noqa: E402
        STEP2_FILE,
        STEP3_FILE,
        load_model_list,
        save_json,
    )

    _papers = load_model_list(STEP2_FILE, Paper)
    _pipeline = FilterPipeline()
    _filtered = _pipeline.run(_papers)
    save_json(_filtered, STEP3_FILE)
    print(f"{len(_filtered)} papers passed filters.")
    print(f"Saved → intermediate_outputs/{STEP3_FILE}")
