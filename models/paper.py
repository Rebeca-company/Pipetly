"""Pydantic schemas for a retrieved scientific paper."""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class FullTextFormat(str, Enum):
    PDF = "pdf"
    XML = "xml"
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

    # Populated during the fetch step
    full_text: Optional[FullText] = None

    # For deduplication
    def unique_id(self) -> str:
        """Return a stable identifier; prefer DOI, fall back to normalised title."""
        if self.doi:
            return self.doi.strip().lower()
        return self.title.strip().lower()

    class Config:
        populate_by_name = True
