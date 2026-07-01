"""Post-extraction full-text length filter.

Applied after Step 5 to keep papers whose full-text length falls within the
accepted range. Deduplication and DOI checking have already been performed in
Step 3 (:class:`processors.metadata_filter.MetadataFilter`).
"""

from __future__ import annotations

import logging
from typing import List

from config import get_settings
from models.paper import Paper

logger = logging.getLogger(__name__)
_s = get_settings()


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
            if content_len < _s.full_text_min_chars:
                discarded_too_short += 1
                logger.debug(
                    "Content too short (%d chars) – discarding '%s'",
                    content_len,
                    paper.title[:60],
                )
                continue

            if content_len > _s.full_text_max_chars:
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
            _s.full_text_min_chars,
            discarded_too_long,
            _s.full_text_max_chars,
        )
        return accepted


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811

    from utils.logger import setup_logging, set_stage_logger

    setup_logging()
    set_stage_logger("step6_post_extraction_filter")

    from utils.intermediate_io import (
        STEP5_FILE,
        STEP6_FILE,
        load_model_list,
        save_json,
    )  # noqa: E402
    from models.paper import Paper  # noqa: F811

    def _main() -> None:
        _papers = load_model_list(STEP5_FILE, Paper)
        logger.info("[Step 6] START | Post-Extraction Filter")
        _filter = FullTextFilter()
        _filtered = _filter.run(_papers)
        save_json(_filtered, STEP6_FILE)
        logger.info("%d papers passed post-extraction filter.", len(_filtered))
        logger.info(
            "[Step 6] DONE | input=%d output=%d | Output: intermediate_outputs/%s",
            len(_papers),
            len(_filtered),
            STEP6_FILE,
        )

    _main()
