"""Pydantic schemas for a retrieved scientific paper."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class FullTextFormat(str, Enum):
    PDF = "pdf"
    XML = "xml"
    HTML = "html"
    PLAIN = "plain"


class FullText(BaseModel):
    format: FullTextFormat
    content: str  # raw text / XML / base-64 PDF bytes
    # True when content is the abstract rather than an actual full-text fetch
    is_abstract_only: bool = False


class Paper(BaseModel):
    """Unified metadata record for a paper from any source."""

    doi: Optional[str] = Field(default=None, description="Canonical DOI (no URL prefix).")
    title: str
    authors: List[str] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    source: str = Field(..., description="API that returned this record (e.g. 'europe_pmc').")
    url: Optional[str] = None
    query_type: Optional[str] = Field(
        default=None,
        description="Query expansion strategy that produced this record "
                    "(structured_boolean | concept_strings).",
    )
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

    # For deduplication
    def unique_id(self) -> str:
        """Return a stable identifier; prefer DOI, fall back to normalised title."""
        if self.doi:
            return self.doi.strip().lower()
        return self.title.strip().lower()

    class Config:
        populate_by_name = True
