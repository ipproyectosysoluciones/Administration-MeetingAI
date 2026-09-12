"""In-memory sliding-window rate limiter (`architecture.md` §7).

No Redis (AGENTS.md §3.16). Store is ``dict[(scope, key), deque[timestamp]]``;
a new timestamp is appended on every check and stale entries are pruned by a
sliding window. A ``Clock`` callable is injected so window expiry is testable
without sleeping. Denied requests still record a timestamp so a sustained burst
cannot extend a bypass window (brute-force hardening).

Redis migration path (§7.2): swap this class for a ``RedisRateLimiter`` exposing
the same ``is_allowed`` interface, then flip ``RATE_LIMIT_BACKEND``.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable

# Callable returning a monotonic timestamp (seconds).
Clock = Callable[[], float]


class InMemoryRateLimiter:
    """Track per-``(scope, key)`` request timestamps within a sliding window."""

    def __init__(self, clock: Clock = time.monotonic) -> None:
        self._clock = clock
        self._store: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def is_allowed(self, scope: str, key: str, limit: int, window_seconds: float) -> bool:
        """Return True if the request is within ``limit`` over ``window_seconds``.

        ``False`` means the caller should reject the request (HTTP 429 at the
        route/dependency layer, out of scope for this primitive).
        """
        now = self._clock()
        window = self._store[(scope, key)]
        window.append(now)
        cutoff = now - window_seconds
        while window and window[0] <= cutoff:
            window.popleft()
        return len(window) <= limit


__all__ = ["Clock", "InMemoryRateLimiter"]
