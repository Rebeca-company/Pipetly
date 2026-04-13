"""Pydantic schemas for extracted protocols and scoring."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ProtocolStep(BaseModel):
    step_number: int
    description: str
    reagents: List[str] = Field(default_factory=list)
    equipment: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    notes: Optional[str] = None
    # Citation marker found in the original text, e.g. "[14]"
    citation_ref: Optional[str] = None


class InheritedReference(BaseModel):
    """Reference to an inherited protocol detail from an ancestor paper."""

    context_phrase: str
    target_doi: Optional[str] = None
    target_title: Optional[str] = None
    target_year: Optional[int] = None
    resolved_fragment: Optional[str] = None
    resolution_depth: Optional[int] = None


class ExtractedProtocol(BaseModel):
    """Full protocol extracted from a single paper."""

    source_doi: Optional[str] = None
    source_title: str
    protocol_text: str = ""
    # Score from 0 to 100 aligned with user intent
    relevance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    inherited_references: List[InheritedReference] = Field(default_factory=list)

    unresolved_citations: List[str] = Field(default_factory=list)


class ScoredProtocol(BaseModel):
    """A ranked protocol ready for output."""

    protocol: ExtractedProtocol
    score: float = Field(..., ge=0.0, le=100.0)
    reasoning: str
