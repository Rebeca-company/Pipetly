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
    queries: List[str] = Field(
        ...,
        min_length=1,
        description="List of concise query strings for literature search APIs.",
    )
