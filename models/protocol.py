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


class ExtractedProtocol(BaseModel):
    """Full protocol extracted from a single paper."""

    source_doi: Optional[str] = None
    source_title: str
    protocol_name: str
    steps: List[ProtocolStep]
    # Raw citation markers that need external resolution
    unresolved_citations: List[str] = Field(default_factory=list)
    raw_bibliography: Optional[str] = None


class ScoredProtocol(BaseModel):
    """A ranked protocol ready for output."""

    protocol: ExtractedProtocol
    score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
