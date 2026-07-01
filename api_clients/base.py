"""Abstract base class shared by all API clients."""

from __future__ import annotations

import asyncio
import datetime as _dt
import html
import logging
import random
import re
import time as _time
from abc import ABC, abstractmethod
from email.utils import parsedate_to_datetime
from typing import List, Optional

import httpx

from config import get_settings
from models.paper import FullText, Paper
from utils.rate_limiter import RateLimiter, get_shared_limiter

logger = logging.getLogger(__name__)
_settings = get_settings()


def clean_title(raw: Optional[str]) -> str:
    """Return a plain-text, whitespace-normalised title.

    * Strips HTML tags (e.g. <i>...</i>) that some APIs include.
    * Unescapes HTML entities.
    * Collapses repeated whitespace and line breaks.
    * Falls back to "Untitled" when the result is empty.
    """

    if not raw:
        return "Untitled"

    text = html.unescape(raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or "Untitled"


class BaseAPIClient(ABC):
    """
    Async HTTP client base.

    Sub-classes implement :py:meth:`search` and :py:meth:`fetch_full_text`.
    """

    #: Sub-class should override these to customise throttling.
    RATE_CALLS: int = 5
    RATE_PERIOD: float = 1.0
    RATE_LIMITER_KEY: Optional[str] = None
    STARTUP_JITTER_MAX: float = 0.0

    def __init__(self) -> None:
        self._limiter = self._init_rate_limiter()
        self._client: Optional[httpx.AsyncClient] = None
        # Diagnostic log: each entry has url, response_time_ms, is_error
        self._request_stats: list[dict] = []
        self._first_request = True

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

    def _init_rate_limiter(self) -> RateLimiter:
        if self.RATE_LIMITER_KEY:
            return get_shared_limiter(
                name=self.RATE_LIMITER_KEY,
                calls=self.RATE_CALLS,
                period=self.RATE_PERIOD,
            )
        return RateLimiter(calls=self.RATE_CALLS, period=self.RATE_PERIOD)

    def _compute_backoff(self, attempt: int) -> float:
        """Return exponential backoff with jitter for the *attempt* (1-indexed)."""
        base_delay = _settings.http_retry_backoff ** max(attempt - 1, 0)
        jitter = random.uniform(0, base_delay * 0.3)
        return base_delay + jitter

    def _retry_after_seconds(self, response: httpx.Response) -> Optional[float]:
        """Parse server-provided retry windows from common rate-limit headers."""
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            value = retry_after.strip()
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    dt = parsedate_to_datetime(value)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_dt.timezone.utc)
                    return max(
                        0.0, (dt - _dt.datetime.now(_dt.timezone.utc)).total_seconds()
                    )
                except (TypeError, ValueError):
                    pass

        reset_at = response.headers.get("X-RateLimit-Reset")
        if reset_at:
            try:
                return max(0.0, float(reset_at) - _time.time())
            except ValueError:
                return None
        return None

    async def _get(self, url: str, **kwargs: object) -> httpx.Response:
        """Rate-limited GET with exponential-backoff retry and timing instrumentation."""
        assert self._client is not None, "Use client as async context manager."
        if self._first_request:
            self._first_request = False
            if self.STARTUP_JITTER_MAX > 0:
                await asyncio.sleep(random.uniform(0, self.STARTUP_JITTER_MAX))
        await self._limiter.acquire()
        t0 = _time.monotonic()
        last_exc: Optional[Exception] = None
        for attempt in range(1, _settings.http_max_retries + 1):
            try:
                resp = await self._client.get(url, **kwargs)  # type: ignore[arg-type]
                resp.raise_for_status()
                elapsed_ms = (_time.monotonic() - t0) * 1000
                self._request_stats.append(
                    {
                        "url": url,
                        "response_time_ms": round(elapsed_ms, 1),
                        "is_error": False,
                    }
                )
                logger.debug(
                    "[%s] GET %s -> %d (%.0f ms)", 
                    self.__class__.__name__, 
                    url, 
                    resp.status_code, 
                    elapsed_ms
                )
                return resp
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                retryable = exc.response.status_code in {429, 500, 502, 503, 504}
                if retryable and attempt < _settings.http_max_retries:
                    wait = self._compute_backoff(attempt)
                    if exc.response.status_code == 429:
                        retry_after = self._retry_after_seconds(exc.response)
                        if retry_after is not None:
                            wait = max(wait, retry_after)
                        await self._limiter.notify_rate_limited(wait)
                    logger.debug(
                        "Retryable HTTP %s from %s - retrying in %.2fs",
                        exc.response.status_code,
                        url,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                elapsed_ms = (_time.monotonic() - t0) * 1000
                self._request_stats.append(
                    {
                        "url": url,
                        "response_time_ms": round(elapsed_ms, 1),
                        "is_error": True,
                    }
                )
                raise
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < _settings.http_max_retries:
                    wait = self._compute_backoff(attempt)
                    logger.debug(
                        "Request error for %s: %s – retrying in %.2fs", url, exc, wait
                    )
                    await asyncio.sleep(wait)
                    continue
                elapsed_ms = (_time.monotonic() - t0) * 1000
                self._request_stats.append(
                    {
                        "url": url,
                        "response_time_ms": round(elapsed_ms, 1),
                        "is_error": True,
                    }
                )
                raise
        elapsed_ms = (_time.monotonic() - t0) * 1000
        self._request_stats.append(
            {"url": url, "response_time_ms": round(elapsed_ms, 1), "is_error": True}
        )
        raise last_exc or RuntimeError("HTTP retries exhausted")

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
