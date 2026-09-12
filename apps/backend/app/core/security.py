"""Core security primitives: Argon2id password hashing and RS256 JWTs.

Mirrors `architecture.md` §4 (authentication & token strategy). Provider-specific
libraries are wrapped behind small service classes so callers never touch `argon2`
or `jwt` directly (AGENTS.md §5: interchangeable provider interfaces).
"""

from __future__ import annotations

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings

# architecture.md §4.3 — fixed by spec (not surfaced in §10.1 env keys).
_ARGON2_HASH_LEN = 32
_ARGON2_SALT_LEN = 16


class PasswordHasher:
    """Argon2id password hashing service.

    Uses ``argon2-cffi`` (Argon2id, the OWASP-recommended memory-hard function)
    directly rather than passlib's ``argon2`` handler, which is unmaintained since
    2020 and broken with modern ``argon2-cffi`` releases. Parameters default to
    ``architecture.md`` §4.3 and may be tuned via ``Settings``.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        config = settings or get_settings()
        self._hasher = Argon2PasswordHasher(
            time_cost=config.argon2_time_cost,
            memory_cost=config.argon2_memory_cost,
            parallelism=config.argon2_parallelism,
            hash_len=_ARGON2_HASH_LEN,
            salt_len=_ARGON2_SALT_LEN,
        )

    def hash(self, password: str) -> str:
        """Return a salted Argon2id encoded password digest."""
        return self._hasher.hash(password)

    def verify(self, password: str, encoded: str) -> bool:
        """Constant-time verify; ``False`` on mismatch or malformed digest."""
        try:
            return self._hasher.verify(encoded, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, encoded: str) -> bool:
        """True when the digest uses stale parameters and should be re-hashed."""
        return self._hasher.check_needs_rehash(encoded)


__all__ = ["PasswordHasher"]
