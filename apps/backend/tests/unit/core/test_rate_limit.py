"""Unit tests for the in-memory rate limiter (TASK-022).

Per `architecture.md` §7: sliding window over a ``dict[(scope, key), deque]``,
no Redis, configurable limits. The primitive returns allow/deny; HTTP 429 is
mapped at the dependency/route layer (PR-3), out of scope for this slice.
"""

from __future__ import annotations

import pytest

from app.core.middleware.rate_limit import InMemoryRateLimiter


class FakeClock:
    """Deterministic monotonic clock for window-expiry tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def limiter(clock: FakeClock) -> InMemoryRateLimiter:
    return InMemoryRateLimiter(clock=clock)


class TestInMemoryRateLimiter:
    def test_rejects_when_limit_exceeded(self, limiter: InMemoryRateLimiter) -> None:
        for _ in range(3):
            assert limiter.is_allowed("ip", "1.2.3.4", limit=3, window_seconds=60) is True
        # The 4th request within the window hits the cap (→ 429 at the route layer).
        assert limiter.is_allowed("ip", "1.2.3.4", limit=3, window_seconds=60) is False

    def test_window_reset_allows_after_expiry(
        self, limiter: InMemoryRateLimiter, clock: FakeClock
    ) -> None:
        for _ in range(3):
            limiter.is_allowed("ip", "1.2.3.4", limit=3, window_seconds=60)
        assert limiter.is_allowed("ip", "1.2.3.4", limit=3, window_seconds=60) is False

        clock.advance(61)  # move past the 60s window
        assert limiter.is_allowed("ip", "1.2.3.4", limit=3, window_seconds=60) is True

    def test_scopes_are_isolated(self, limiter: InMemoryRateLimiter) -> None:
        # Same key string, different scope → independent buckets.
        for _ in range(3):
            limiter.is_allowed("ip", "shared", limit=3, window_seconds=60)
        assert limiter.is_allowed("ip", "shared", limit=3, window_seconds=60) is False
        assert limiter.is_allowed("user", "shared", limit=3, window_seconds=60) is True

    def test_keys_are_isolated(self, limiter: InMemoryRateLimiter) -> None:
        for _ in range(3):
            limiter.is_allowed("ip", "a", limit=3, window_seconds=60)
        assert limiter.is_allowed("ip", "a", limit=3, window_seconds=60) is False
        assert limiter.is_allowed("ip", "b", limit=3, window_seconds=60) is True

    def test_sliding_window_prunes_individually(
        self, limiter: InMemoryRateLimiter, clock: FakeClock
    ) -> None:
        # Three hits at t=0: the third exceeds limit=2.
        assert limiter.is_allowed("ip", "x", limit=2, window_seconds=60) is True
        assert limiter.is_allowed("ip", "x", limit=2, window_seconds=60) is True
        assert limiter.is_allowed("ip", "x", limit=2, window_seconds=60) is False

        # t=40: the t=0 events are still in-window (age 40 < 60) → still limited.
        clock.advance(40)
        assert limiter.is_allowed("ip", "x", limit=2, window_seconds=60) is False

        # t=61: t=0 events (age 61 > 60) are pruned; only the t=40 event remains,
        # so the t=61 hit is allowed — proving per-timestamp sliding (not a reset).
        clock.advance(21)
        assert limiter.is_allowed("ip", "x", limit=2, window_seconds=60) is True
