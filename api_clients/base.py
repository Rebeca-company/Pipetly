"""Abstract base class shared by all API clients."""
from __future__ import annotations

import logging
import time as _time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from config import get_settings
from models.paper import FullText, Paper
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
_settings = get_settings()


class BaseAPIClient(ABC):
    """
    Async HTTP client base.

    Sub-classes implement :py:meth:`search` and :py:meth:`fetch_full_text`.
    """

    #: Sub-class should override these to customise throttling.
    RATE_CALLS: int = 5
    RATE_PERIOD: float = 1.0

    def __init__(self) -> None:
        self._limiter = RateLimiter(calls=self.RATE_CALLS, period=self.RATE_PERIOD)
        self._client: Optional[httpx.AsyncClient] = None
        # Diagnostic log: each entry has url, response_time_ms, is_error
        self._request_stats: list[dict] = []

    # ── Context manager ───────────────────────────────────────────────────────

    async def __aenter__(self) -> "BaseAPIClient":
        self._client = httpx.AsyncClient(
            timeout=_settings.http_timeout,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _get(self, url: str, **kwargs: object) -> httpx.Response:
        """Rate-limited GET with exponential-backoff retry and timing instrumentation."""
        assert self._client is not None, "Use client as async context manager."
        await self._limiter.acquire()
        t0 = _time.monotonic()
        last_exc: Exception = RuntimeError("unreachable")
        for attempt in range(_settings.http_max_retries):
            try:
                resp = await self._client.get(url, **kwargs)  # type: ignore[arg-type]
                resp.raise_for_status()
                elapsed_ms = (_time.monotonic() - t0) * 1000
                self._request_stats.append({"url": url, "response_time_ms": round(elapsed_ms, 1), "is_error": False})
                return resp
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    import asyncio
                    wait = _settings.http_retry_backoff ** attempt
                    logger.warning("Rate-limited by %s – retrying in %.1fs", url, wait)
                    await asyncio.sleep(wait)
                    last_exc = exc
                else:
                    elapsed_ms = (_time.monotonic() - t0) * 1000
                    self._request_stats.append({"url": url, "response_time_ms": round(elapsed_ms, 1), "is_error": True})
                    raise
            except httpx.RequestError as exc:
                import asyncio
                wait = _settings.http_retry_backoff ** attempt
                logger.warning("Request error for %s: %s – retrying in %.1fs", url, exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc
        elapsed_ms = (_time.monotonic() - t0) * 1000
        self._request_stats.append({"url": url, "response_time_ms": round(elapsed_ms, 1), "is_error": True})
        raise last_exc

    # ── Abstract interface ────────────────────────────────────────────────────

    async def _get_bytes(self, url: str, **kwargs: object) -> bytes:
        """Rate-limited GET returning raw bytes (for binary content such as PDFs)."""
        resp = await self._get(url, **kwargs)
        return resp.content

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def search(self, query: str, max_results: int) -> List[Paper]:
        """Keyword / boolean search; return a list of :class:`Paper` objects."""

    @abstractmethod
    async def fetch_full_text(self, paper: Paper) -> Optional[FullText]:
        """Fetch full text for *paper*; return a :class:`FullText` or ``None``."""
