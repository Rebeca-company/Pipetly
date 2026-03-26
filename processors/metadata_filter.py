"""Step 2 – Metadata Filtering.

Remove duplicate papers and entries that lack a DOI so that downstream
steps (full-text retrieval, protocol extraction) operate on a clean,
deduplicated set of uniquely identifiable records.
"""
from __future__ import annotations

import logging
import unicodedata
import re
from typing import Dict, List

from models.paper import Paper

logger = logging.getLogger(__name__)

# Normalise a title for duplicate comparison: lowercase, collapse whitespace,
# strip leading/trailing punctuation.
_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s]")  # elimina puntuación

def _normalise_title(title: str) -> str:
    # 1. Quitar acentos: "Détection" → "Detection"
    title = unicodedata.normalize("NFKD", title)
    title = title.encode("ascii", "ignore").decode("ascii")
    # 2. Lowercase
    title = title.lower()
    # 3. Eliminar puntuación: "deep-learning" → "deep learning"
    title = _PUNCT_RE.sub("", title)
    # 4. Colapsar espacios
    title = _WS_RE.sub("", title).strip()
    return title


def _completeness(paper: Paper) -> int:
    """Return a metadata-completeness score (higher = more complete)."""
    score = 0
    if paper.doi:
        score += 1
    if paper.title:
        score += 1
    if paper.abstract:
        score += 3        # abstract is high-value
    if paper.authors:
        score += min(len(paper.authors), 10)
    if paper.year:
        score += 1
    if paper.url:
        score += 1
    return score


class MetadataFilter:
    """Step 2: deduplicate by DOI and title, keep the most complete record."""

    def run(self, papers: List[Paper]) -> List[Paper]:
        """
        Filter *papers* and return a deduplicated list of papers that all
        possess a canonical DOI.

        Rules applied in order:

        1. **DOI required** – papers that carry no DOI are discarded.
        2. **DOI deduplication** – papers sharing the same DOI
           (case-insensitive) are collapsed; the record with the highest
           metadata-completeness score is kept.
        3. **Title deduplication** – among the surviving records, papers
           sharing the same normalised title (but different DOIs) are also
           collapsed; again the most complete record is kept.
        """
        no_doi: int = 0

        # ── Pass 1: DOI deduplication ─────────────────────────────────────
        doi_best: Dict[str, Paper] = {}
        for paper in papers:
            if not paper.doi:
                no_doi += 1
                logger.debug("No DOI – discarding '%s'", paper.title[:60])
                continue
            uid = paper.doi.strip().lower()
            if uid not in doi_best or _completeness(paper) > _completeness(doi_best[uid]):
                doi_best[uid] = paper

        doi_dupes = len(papers) - no_doi - len(doi_best)

        # ── Pass 2: title deduplication ───────────────────────────────────
        title_best: Dict[str, Paper] = {}
        for paper in doi_best.values():
            norm = _normalise_title(paper.title)
            if not norm:
                title_best[paper.doi.strip().lower()] = paper  # keep by DOI if no title
                continue
            if norm not in title_best or _completeness(paper) > _completeness(title_best[norm]):
                if norm in title_best:
                    logger.debug(
                        "Title duplicate – keeping '%s' (%s) over '%s' (%s)",
                        paper.title[:60], paper.doi,
                        title_best[norm].title[:60], title_best[norm].doi,
                    )
                title_best[norm] = paper

        title_dupes = len(doi_best) - len(title_best)
        accepted = list(title_best.values())

        logger.info(
            "Step 2 – Metadata filtering: %d raw → %d accepted "
            "(%d no-DOI discarded, %d DOI-duplicates removed, "
            "%d title-duplicates removed).",
            len(papers),
            len(accepted),
            no_doi,
            doi_dupes,
            title_dupes,
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

    from utils.intermediate_io import STEP2_FILE, STEP3_FILE, load_model_list, save_json
    from models.paper import Paper  # noqa: F811

    _papers = load_model_list(STEP2_FILE, Paper)
    _filtered = MetadataFilter().run(_papers)
    save_json(_filtered, STEP3_FILE)
    print(f"{len(_filtered)} papers passed metadata filter.")
    print(f"Saved → intermediate_outputs/{STEP3_FILE}")
