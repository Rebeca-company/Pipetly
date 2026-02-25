"""Token-bucket rate limiter for async HTTP clients."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field


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
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def acquire(self) -> None:
        """Block until a token is available."""
        async with self._lock:
            now = time.monotonic()
            # Purge timestamps outside the current window
            self._timestamps = [t for t in self._timestamps if now - t < self.period]
            if len(self._timestamps) >= self.calls:
                sleep_for = self.period - (now - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                # Re-purge after sleeping
                now = time.monotonic()
                self._timestamps = [t for t in self._timestamps if now - t < self.period]
            self._timestamps.append(time.monotonic())
