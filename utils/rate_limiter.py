"""Token-bucket rate limiter for async HTTP clients."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

_shared_limiters: dict[str, "RateLimiter"] = {}


@dataclass
class RateLimiter:
    """
    Simple async token-bucket rate limiter.

    Parameters
    ----------
    calls : int
        Maximum number of calls allowed in ``period`` seconds.
    period : float
        Window length in seconds.
    """

    calls: int = 5
    period: float = 1.0
    _timestamps: list[float] = field(default_factory=list, init=False, repr=False)
    _blocked_until: float = field(default=0.0, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def acquire(self) -> None:
        """Block until a token is available."""
        while True:
            async with self._lock:
                now = time.monotonic()
                self._timestamps = [
                    t for t in self._timestamps if now - t < self.period
                ]
                cooldown_wait = max(0.0, self._blocked_until - now)

                window_wait = 0.0
                if len(self._timestamps) >= self.calls:
                    window_wait = max(0.0, self.period - (now - self._timestamps[0]))

                sleep_for = max(cooldown_wait, window_wait)
                if sleep_for <= 0:
                    self._timestamps.append(now)
                    return

            await asyncio.sleep(sleep_for)

    async def notify_rate_limited(self, retry_after_seconds: float) -> None:
        """Apply a shared cooldown so concurrent callers back off together."""
        if retry_after_seconds <= 0:
            return
        async with self._lock:
            self._blocked_until = max(
                self._blocked_until,
                time.monotonic() + retry_after_seconds,
            )


def get_shared_limiter(name: str, calls: int, period: float) -> RateLimiter:
    """Return a shared ``RateLimiter`` instance for *name*.

    Ensures callers reuse the same limiter per logical upstream (e.g., NCBI)
    so distributed client instances respect a global quota.
    """
    limiter = _shared_limiters.get(name)
    if limiter is None:
        limiter = RateLimiter(calls=calls, period=period)
        _shared_limiters[name] = limiter
        return limiter

    # Update limits if the shared limiter already exists with different caps.
    limiter.calls = calls
    limiter.period = period
    return limiter
