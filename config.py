"""
Central configuration for Pipetly.
All secrets are read from environment variables so nothing sensitive lives
in source code.  Copy .env.example → .env and fill in your keys.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# intermediate_outputs is resolved relative to config.py location
INTERMEDIATE_DIR: Path = Path(__file__).resolve().parent / "intermediate_outputs"


class Settings(BaseSettings):
    """Application settings schema and defaults."""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # Model used for all LLM tasks (query expansion, full-text extraction, formatting, etc.).
    llm_model_general: str = "deepseek/deepseek-v4-flash" 
    # google/gemini-3-flash-preview
    # deepseek/deepseek-v4-flash
    # xiaomi/mimo-v2.5

    # Precios manuales por 1M de tokens (se usan si no se obtienen de OpenRouter)
    llm_cost_input_usd_per_1m: float = 0.50
    llm_cost_output_usd_per_1m: float = 3.00
    
    # Flag para decidir si consultar los precios en tiempo real a OpenRouter
    fetch_openrouter_pricing: bool = True

    # ── External APIs (all optional – clients degrade gracefully) ─────────────
    elsevier_api_key: str = Field(default="", alias="ELSEVIER_API_KEY")
    elsevier_inst_token: str = Field(default="", alias="ELSEVIER_INST_TOKEN")
    semantic_scholar_api_key: str = Field(default="", alias="SEMANTIC_SCHOLAR_API_KEY")
    # Unpaywall requires a contact e-mail instead of an API key
    unpaywall_email: str = Field(default="", alias="UNPAYWALL_EMAIL")
    ncbi_api_key: str = Field(default="", alias="NCBI_API_KEY")

    # ── HTTP ──────────────────────────────────────────────────────────────────
    http_timeout: float = 30.0  # seconds per request
    http_max_retries: int = 4
    http_retry_backoff: float = 2.0  # exponential-backoff base

    # ── Pipeline ─────────────────────────────────────────────────────────────
    max_papers_per_source: int = 3  # fetch limit per API
    max_citation_depth: int = 2  # recursive citation-investigator depth
    full_text_min_chars: int = 10_000  # accepted minimum full-text length
    full_text_max_chars: int = 200_000  # accepted maximum full-text length
    top_k_protocols: int = 3  # how many to score/return
    llm_max_concurrent: int = 20  # shared LLM concurrency for Steps 7, 8 and 9

    # ── Output ────────────────────────────────────────────────────────────────
    output_dir: str = "output"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    export_stage_logs: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings (cached)."""
    return Settings()
