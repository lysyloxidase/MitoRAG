from __future__ import annotations

import asyncio

from mitorag_web.rate_limiter import AsyncRateLimiter, pubmed_rate_limiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_pubmed_rate_limiter_never_exceeds_three_requests_per_second() -> None:
    clock = FakeClock()
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock.now += seconds

    async def run() -> AsyncRateLimiter:
        limiter = AsyncRateLimiter(3.0, sleep=fake_sleep, clock=clock)
        for _ in range(5):
            await limiter.acquire()
        return limiter

    limiter = asyncio.run(run())

    gaps = [right - left for left, right in zip(limiter.acquired_at, limiter.acquired_at[1:])]
    assert all(gap + 1e-12 >= (1 / 3) for gap in gaps)
    assert sleeps


def test_pubmed_rate_limiter_uses_free_key_higher_limit() -> None:
    assert pubmed_rate_limiter().rate_per_second == 3.0
    assert pubmed_rate_limiter(api_key="free-key").rate_per_second == 10.0
