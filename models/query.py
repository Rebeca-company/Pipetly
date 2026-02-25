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
    keyword_queries: List[str] = Field(
        ...,
        min_length=1,
        description="Boolean / keyword search strings suitable for PubMed-style APIs.",
    )
    semantic_queries: List[str] = Field(
        ...,
        min_length=1,
        description="Natural-language sentences optimised for vector / semantic search.",
    )
