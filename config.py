"""
Central configuration for Pipetly.
All secrets are read from environment variables so nothing sensitive lives
in source code.  Copy .env.example → .env and fill in your keys.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Model used for tasks that require reading long full-text paper content.
    gemini_model_fulltext: str = Field(
        default="google/gemini-3-flash-preview",
        alias="GEMINI_MODEL_FULLTEXT",
    )
    # Model used for the rest of LLM tasks (query expansion, formatting, etc.).
    gemini_model_general: str = Field(
        default="google/gemini-3-flash-preview",
        alias="GEMINI_MODEL_GENERAL",
    )
    # Backward-compatible fallback for older code paths/env files.
    gemini_model: str = "google/gemini-3-flash-preview"

    # ── External APIs (all optional – clients degrade gracefully) ─────────────
    elsevier_api_key: str = Field(default="", alias="ELSEVIER_API_KEY")
    elsevier_inst_token: str = Field(default="", alias="ELSEVIER_INST_TOKEN")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    # Unpaywall requires a contact e-mail instead of an API key
    unpaywall_email: str = Field(default="", alias="UNPAYWALL_EMAIL")
    ncbi_api_key: str = Field(default="", alias="NCBI_API_KEY")

    # ── HTTP ──────────────────────────────────────────────────────────────────
    http_timeout: float = 30.0          # seconds per request
    http_max_retries: int = 4
    http_retry_backoff: float = 2.0     # exponential-backoff base

    # ── Pipeline ─────────────────────────────────────────────────────────────
    max_papers_per_source: int = 3      # fetch limit per API
    max_citation_depth: int = 2        # recursive citation-investigator depth
    full_text_min_chars: int = 10_000   # accepted minimum full-text length
    full_text_max_chars: int = 200_000  # accepted maximum full-text length
    top_k_protocols: int = 5            # how many to score/return
    llm_max_concurrent: int = 20        # shared LLM concurrency for Steps 7, 9 and 10

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir: str = "output"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
