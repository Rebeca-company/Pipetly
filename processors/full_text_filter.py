"""Post-extraction full-text length filter.

Applied after Step 5 to keep papers whose full-text length falls within the
accepted range. Deduplication and DOI checking have already been performed in
Step 2 (:class:`processors.metadata_filter.MetadataFilter`).
"""
from __future__ import annotations

import logging
from typing import List

from models.paper import Paper

logger = logging.getLogger(__name__)

MIN_CHARS = 3_000
MAX_CHARS = 3_000_000


class FullTextFilter:
    """Post-extraction filter: keep only papers within the configured length range."""

    def run(self, papers: List[Paper]) -> List[Paper]:
        accepted: list[Paper] = []
        discarded_no_text = discarded_too_short = discarded_too_long = 0

        for paper in papers:
            # Keep this safety check to avoid failing on malformed inputs.
            if not paper.full_text or not paper.full_text.content.strip():
                discarded_no_text += 1
                logger.debug("No full text – discarding '%s'", paper.title[:60])
                continue

            content_len = len(paper.full_text.content)
            if content_len < MIN_CHARS:
                discarded_too_short += 1
                logger.debug(
                    "Content too short (%d chars) – discarding '%s'",
                    content_len,
                    paper.title[:60],
                )
                continue

            if content_len > MAX_CHARS:
                discarded_too_long += 1
                logger.debug(
                    "Content too long (%d chars) – discarding '%s'",
                    content_len,
                    paper.title[:60],
                )
                continue

            accepted.append(paper)

        logger.info(
            "Filter results: %d accepted | %d no-full-text | %d < %d chars | %d > %d chars.",
            len(accepted),
            discarded_no_text,
            discarded_too_short,
            MIN_CHARS,
            discarded_too_long,
            MAX_CHARS,
        )
        return accepted


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import (
        STEP5_FILE,
        STEP6_FILE,
        load_model_list,
        save_json,
    )  # noqa: E402
    from models.paper import Paper  # noqa: F811

    _papers = load_model_list(STEP5_FILE, Paper)
    _filter = FullTextFilter()
    _filtered = _filter.run(_papers)
    save_json(_filtered, STEP6_FILE)
    print(f"{len(_filtered)} papers passed post-extraction filter.")
    print(f"Saved → intermediate_outputs/{STEP6_FILE}")
