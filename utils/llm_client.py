import logging
from typing import Any, Optional

from config import get_settings

_s = get_settings()
logger = logging.getLogger(__name__)


class BaseLLMProcessor:
    """Base class for processors that make calls to OpenRouter/LLMs."""

    def __init__(self, step_name: str) -> None:
        """
        Args:
            step_name: A short string (e.g., '1', '7', '8', '9') used for telemetry.
        """
        self.step_name = step_name
        self._base = _s.openrouter_base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {_s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/pipetly",
            "X-Title": "Pipetly",
        }
        self._llm_token_events: list[dict[str, int | str]] = []
        self._llm_call_count = 0

    def get_llm_token_events(self) -> list[dict[str, int | str]]:
        """Return per-call token telemetry records."""
        return list(self._llm_token_events)

    def _record_llm_usage(
        self,
        response_json: dict[str, Any],
        step_key: str | None = None,
        generation_time_ms: Optional[float] = None,
    ) -> None:
        """Extract and store token usage (and optional timing) from an OpenRouter response.

        Args:
            response_json: The raw JSON response from the OpenRouter API.
            step_key: Override the default step name stored in ``self.step_name``.
            generation_time_ms: Total wall-clock time of the HTTP request in ms.
                When provided, ``tokens_per_second`` and ``output_tokens_per_second``
                are computed and stored alongside the event.
        """
        actual_step = step_key if step_key is not None else self.step_name
        usage = response_json.get("usage") or {}

        in_tokens = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or usage.get("promptTokens")
            or 0
        )
        out_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or usage.get("completionTokens")
            or 0
        )
        total_tokens = int(usage.get("total_tokens") or (in_tokens + out_tokens))

        # ── Timing fields ──────────────────────────────────────────────────────
        gen_ms: Optional[float] = (
            round(generation_time_ms, 2) if generation_time_ms is not None else None
        )
        tps: Optional[float] = None
        out_tps: Optional[float] = None
        if gen_ms and gen_ms > 0:
            seconds = gen_ms / 1000.0
            tps = round(total_tokens / seconds, 2)
            out_tps = round(out_tokens / seconds, 2)

        self._llm_call_count += 1
        event: dict[str, Any] = {
            "step": actual_step,
            "call_index": self._llm_call_count,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "total_tokens": total_tokens,
            "generation_time_ms": gen_ms,
            "tokens_per_second": tps,
            "output_tokens_per_second": out_tps,
        }
        self._llm_token_events.append(event)

        logger.info(
            "LLM step %s tokens (call %d) - in=%d out=%d total=%d gen_time=%.0fms",
            actual_step,
            self._llm_call_count,
            in_tokens,
            out_tokens,
            total_tokens,
            gen_ms or 0,
        )
