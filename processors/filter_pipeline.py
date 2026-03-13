"""Post-extraction filter pipeline.

Applied after Step 4 (text extraction) to retain only papers with usable
full text that contain a recognisable methodology section.  Deduplication
and DOI checking have already been performed in Step 2
(:class:`processors.metadata_filter.MetadataFilter`).
"""
from __future__ import annotations

import logging
import re
from typing import List

from models.paper import Paper

logger = logging.getLogger(__name__)

# Regex pattern that must match at least one methodology-like section header
_METHODS_RE = re.compile(
    r"(?imx)"                   # Case-insensitive, Multiline, Verbose
    r"^\s*("                    # Start of line + optional whitespace
    # --- Estándar Experimental ---
    r"materials?\s*(?:and|&)\s*methods?"
    r"|methods?\s*(?:and|&)\s*materials?"
    r"|experimental\s+(?:sections?|procedures?|methods?|setup|design)"
    
    # --- Variaciones Médicas/Clínicas ---
    r"|patients?\s*(?:and|&)\s*methods?"
    r"|clinical\s+protocols?"
    r"|study\s+(?:design|methods?)"
    
    # --- Variaciones de Ingeniería/CS ---
    r"|proposed\s+(?:methods?|approach|architecture|system)"
    r"|implementation\s+details?"
    r"|algorithm\s+descriptions?"
    
    # --- Términos Genéricos Densos ---
    r"|methodology"
    r"|procedures?"
    r"|methods?"
    r"|protocols?"
    r"|methods?\s+and\s+analysis"
    r")\s*$"                    # Fin de la línea
)


class FilterPipeline:
    """Post-extraction filter: require full text and a detectable methods section."""

    def run(self, papers: List[Paper]) -> List[Paper]:
        accepted: list[Paper] = []
        discarded_ft = discarded_methods = 0

        for paper in papers:
            # 1. Must have full text with non-empty content
            if not paper.full_text or not paper.full_text.content.strip():
                discarded_ft += 1
                logger.debug("No full text – discarding '%s'", paper.title[:60])
                continue

            # 2. Methods-section check (waived for abstract-only content)
            if not paper.full_text.is_abstract_only:
                if not _METHODS_RE.search(paper.full_text.content):
                    discarded_methods += 1
                    logger.debug(
                        "No methods section – discarding '%s'", paper.title[:60]
                    )
                    continue

            accepted.append(paper)

        logger.info(
            "Filter results: %d accepted | %d no-full-text | %d no-methods-section.",
            len(accepted),
            discarded_ft,
            discarded_methods,
        )
        return accepted


# ── Stand-alone entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    import logging  # noqa: F811

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )

    from utils.intermediate_io import STEP5_FILE, load_model_list  # noqa: E402
    from models.paper import Paper  # noqa: F811

    _papers = load_model_list(STEP5_FILE, Paper)
    _pipeline = FilterPipeline()
    _filtered = _pipeline.run(_papers)
    print(f"{len(_filtered)} papers passed post-extraction filter.")
