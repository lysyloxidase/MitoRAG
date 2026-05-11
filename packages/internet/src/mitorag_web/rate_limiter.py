"""Respectful async rate limiting utilities."""

from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, List, Optional

SleepFn = Callable[[float], Awaitable[None]]
ClockFn = Callable[[], float]


class AsyncRateLimiter:
    """Simple lock-protected interval limiter.

    A 3 req/s limiter spaces acquisitions by at least 333 ms, which is stricter
    than a sliding-window burst limiter and keeps PubMed comfortably below its
    unauthenticated limit.
    """

    def __init__(
        self,
        rate_per_second: float,
        sleep: SleepFn = asyncio.sleep,
        clock: ClockFn = time.monotonic,
    ) -> None:
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
        self.rate_per_second = rate_per_second
        self.min_interval_seconds = 1.0 / rate_per_second
        self._sleep = sleep
        self._clock = clock
        self._lock: Optional[asyncio.Lock] = None
        self._lock_loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_acquired: Optional[float] = None
        self.acquired_at: List[float] = []

    async def acquire(self) -> None:
        async with self._loop_lock():
            now = self._clock()
            if self._last_acquired is not None:
                elapsed = now - self._last_acquired
                wait_seconds = self.min_interval_seconds - elapsed
                if wait_seconds > 0:
                    await self._sleep(wait_seconds)
                    now = self._clock()
            self._last_acquired = now
            self.acquired_at.append(now)

    def _loop_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if self._lock is None or self._lock_loop is not loop:
            self._lock = asyncio.Lock()
            self._lock_loop = loop
        return self._lock


def pubmed_rate_limiter(api_key: Optional[str] = None) -> AsyncRateLimiter:
    return AsyncRateLimiter(10.0 if api_key else 3.0)
