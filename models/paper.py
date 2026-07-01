"""Pydantic schemas for a retrieved scientific paper."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class FullTextFormat(str, Enum):
    PDF = "pdf"
    XML = "xml"
    HTML = "html"
    PLAIN = "plain"


class FullText(BaseModel):
    format: FullTextFormat
    content: str  # raw text / XML / base-64 PDF bytes


class Paper(BaseModel):
    """Unified metadata record for a paper from any source."""

    doi: Optional[str] = Field(
        default=None, description="Canonical DOI (no URL prefix)."
    )
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    source: str = Field(
        ..., description="API that returned this record (e.g. 'europe_pmc')."
    )
    url: Optional[str] = None
    response_time_ms: Optional[float] = Field(
        default=None,
        description="Round-trip time of the search() call that returned this record (ms).",
    )
    is_error: bool = Field(
        default=False,
        description="True when the search call raised an exception; record is a placeholder.",
    )

    # Populated during the full-text retrieval step
    full_text: Optional[FullText] = None
    ft_response_time_ms: Optional[float] = Field(
        default=None,
        description="Response time of the winning fetch_full_text() call (ms).",
    )
    ft_retrieved_by: Optional[str] = Field(
        default=None,
        description="Short name of the API client that returned full text (e.g. 'europe_pmc').",
    )
    ft_attempts: List[dict] = Field(
        default_factory=list,
        description="Telemetry: list of dicts describing full-text fetch attempts.",
    )


class SearchTelemetry(BaseModel):
    """Telemetry for a single search API attempt."""
    query: str
    client: str
    elapsed_ms: float
    is_error: bool
    results_count: int


class SearchResult(BaseModel):
    """Output of Step 2 (PaperSearcher)."""
    papers: List[Paper]
    telemetry: List[SearchTelemetry]
