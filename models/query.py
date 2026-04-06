"""Pydantic schemas for query-expansion output."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class ExpandedQuery(BaseModel):
    """Output produced by the Query Expansion Module."""

    intent: str = Field(
        ...,
        description="One-sentence summary of what the user is looking for.",
    )
    concept_strings: List[str] = Field(
        ...,
        min_length=1,
        description="Clean keyword strings for OpenAlex/Crossref/Unpaywall.",
    )
