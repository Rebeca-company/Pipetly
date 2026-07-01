"""Pydantic schemas for extracted protocols and scoring."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


# ── LLM output models (one per step that calls the LLM) ──────────────────────


class ProtocolIntervalOutput(BaseModel):
    """Raw LLM output from Step 7.1 – protocol interval extraction."""

    protocol_text: str
    relevance_score: float


class InheritedReferenceItem(BaseModel):
    """Single item returned by Step 7.2 before deduplication."""

    context_phrase: str
    search_intent: Optional[str] = None
    reference_text: Optional[str] = None


class InheritedReferencesOutput(BaseModel):
    """Raw LLM output from Step 7.2 – inherited reference extraction."""

    inherited_references: List[InheritedReferenceItem] = Field(default_factory=list)


class ReferenceMetadataOutput(BaseModel):
    """Raw LLM output from Step 7.3 – bibliographic metadata resolver."""

    target_doi: Optional[str] = None
    target_title: Optional[str] = None
    target_year: Optional[int] = None


class ScoringOutput(BaseModel):
    """Raw LLM output from Step 8 – protocol re-scorer."""

    relevance_score: float
    scoring_justification: str


# ── Pipeline data models ──────────────────────────────────────────────────────


class InheritedReference(BaseModel):
    """Reference to an inherited protocol detail from an ancestor paper."""

    search_intent: Optional[str] = None
    reference_text: Optional[str] = None
    context_phrase: str
    target_doi: Optional[str] = None
    target_title: Optional[str] = None
    target_year: Optional[int] = None
    resolved_fragment: Optional[str] = None
    resolution_depth: Optional[int] = None
    # Monitoring field: where inherited full text came from.
    full_text_found_by: Optional[str] = None


class ExtractedProtocol(BaseModel):
    """Full protocol extracted from a single paper."""

    source_doi: Optional[str] = None
    source_title: str
    protocol_text: str = ""
    # Score from 0 to 100 aligned with user intent
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    # Monitoring field: short LLM rationale for Step 8 score.
    scoring_justification: Optional[str] = None
    inherited_references: List[InheritedReference] = Field(default_factory=list)
    recursion_depth: int = Field(default=0, ge=0)
    nested_protocols: List["ExtractedProtocol"] = Field(default_factory=list)


class ScoredProtocol(BaseModel):
    """A ranked protocol ready for output."""

    protocol: ExtractedProtocol
    score: float = Field(..., ge=0.0, le=100.0)


ExtractedProtocol.model_rebuild()
