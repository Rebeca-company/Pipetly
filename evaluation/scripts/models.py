"""Pydantic models for the LLM-judge evaluation pipeline.

Used exclusively by ``llm_judge.py``.
Sources are defined per-entry in the benchmark data (any number of models).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── LLM judge output ──────────────────────────────────────────────────────────


class MetricScore(BaseModel):
    """Score and justification for a single evaluation metric."""

    score: int = Field(..., ge=1, le=5)
    justification: str


class JudgeResult(BaseModel):
    """Full 6-metric evaluation result for one protocol, from one judge call."""

    relevance: MetricScore
    completeness: MetricScore
    parameter_consistency: MetricScore
    executability: MetricScore
    structural_coherence: MetricScore
    conciseness: MetricScore

    @property
    def mean_score(self) -> float:
        """Arithmetic mean of the six metric scores."""
        scores = [
            self.relevance.score,
            self.completeness.score,
            self.parameter_consistency.score,
            self.executability.score,
            self.structural_coherence.score,
            self.conciseness.score,
        ]
        return sum(scores) / len(scores)

    def to_score_dict(self) -> Dict[str, float]:
        """Return a flat dict mapping metric name → score (float)."""
        return {
            "relevance": float(self.relevance.score),
            "completeness": float(self.completeness.score),
            "parameter_consistency": float(self.parameter_consistency.score),
            "executability": float(self.executability.score),
            "structural_coherence": float(self.structural_coherence.score),
            "conciseness": float(self.conciseness.score),
            "mean": self.mean_score,
        }


# ── Benchmark input ───────────────────────────────────────────────────────────


class EvaluationEntry(BaseModel):
    """One evaluation case: a query and one protocol text per source.

    ``protocols`` is a free-form dict keyed by source name (e.g.
    ``"pipetly_model1"``, ``"gemini_pro"``, ``"bioprobench"``).
    Add or remove keys to extend the benchmark to any number of models.
    Sources with empty or missing text are skipped automatically.
    """

    id: str = Field(..., description="Unique identifier for this benchmark case")
    query: str = Field(..., description="The user query / technique description")
    protocols: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of source_name → protocol text",
    )

    @property
    def active_sources(self) -> list[str]:
        """Source names that have non-empty protocol text (skip placeholders)."""
        return [
            src for src, text in self.protocols.items()
            if text.strip() and "PLACEHOLDER" not in text
        ]


# ── Per-run results ───────────────────────────────────────────────────────────


class SourceResult(BaseModel):
    """Judge result for a single (entry, source, run) triplet."""

    entry_id: str
    source: str
    run: int
    result: Optional[JudgeResult] = None
    error: Optional[str] = None


class RunResult(BaseModel):
    """All source results for a single run."""

    run: int
    results: List[SourceResult] = Field(default_factory=list)


# ── Constants ─────────────────────────────────────────────────────────────────

METRIC_NAMES = [
    "relevance",
    "completeness",
    "parameter_consistency",
    "executability",
    "structural_coherence",
    "conciseness",
    "mean",
]
