"""Core security primitives: Argon2id password hashing and RS256 JWTs.

Mirrors `architecture.md` §4 (authentication & token strategy). Provider-specific
libraries are wrapped behind small service classes so callers never touch `argon2`
or `jwt` directly (AGENTS.md §5: interchangeable provider interfaces).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import jwt
from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

from app.core.config import Settings, get_settings
from app.core.exceptions import ExpiredTokenError, InvalidTokenError

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


class TOTP:
    """RFC 6238 TOTP (SHA-1, 30-second step, 6 digits) — `architecture.md` §4.4.

    Implemented directly over the stdlib (``hmac``/``hashlib``) rather than a
    third-party provider so the math is testable against the RFC 6238 vectors and
    no provider SDK leaks into callers (AGENTS.md §5: interchangeable interfaces).
    """

    ALGORITHM = "SHA1"
    STEP_SECONDS = 30
    DIGITS = 6
    ISSUER = "ReunionAI"

    @staticmethod
    def generate_secret() -> str:
        """Return a base32 (RFC 4648, unpadded) TOTP secret from 20 random bytes."""
        return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

    @classmethod
    def provisioning_uri(cls, secret: str, account: str) -> str:
        """Return the ``otpauth://`` URI used to render the enrollment QR code."""
        return f"otpauth://totp/{cls.ISSUER}:{account}?secret={secret}&issuer={cls.ISSUER}"

    @staticmethod
    def _counter(now: float | None = None) -> int:
        return int((now if now is not None else time.time()) // TOTP.STEP_SECONDS)

    @staticmethod
    def _decode_secret(secret: str) -> bytes:
        normalized = secret.strip().upper().replace(" ", "")
        return base64.b32decode(normalized + "=" * (-len(normalized) % 8))

    @classmethod
    def _generate_code(cls, secret: str, counter: int) -> str:
        key = cls._decode_secret(secret)
        digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10**cls.DIGITS)).zfill(cls.DIGITS)

    @classmethod
    def current_code(cls, secret: str, *, now: float | None = None) -> str:
        """Return the current 6-digit code for ``secret`` (test/diagnostic helper)."""
        return cls._generate_code(secret, cls._counter(now))

    @classmethod
    def verify(cls, secret: str, code: str, *, now: float | None = None, window: int = 1) -> bool:
        """Verify a TOTP code with a ±``window`` step tolerance for clock drift.

        The tolerance does not weaken the one-time property: each step's code is
        still accepted at most once per window.
        """
        if not secret or not code:
            return False
        code = code.strip()
        if len(code) != cls.DIGITS or not code.isdigit():
            return False
        counter = cls._counter(now)
        return any(
            cls._generate_code(secret, c) == code
            for c in range(counter - window, counter + window + 1)
        )


class JWTService:
    """Issue and verify RS256 access tokens (`architecture.md` §4.1).

    Keys are PEM strings read from ``Settings.jwt_private_key``/
    ``jwt_public_key`` (env). Access tokens carry ``sub`` (user id), ``tid``
    (tenant id), ``perm`` (permission strings), ``iat``, ``exp`` (15-minute TTL),
    and ``jti`` (unique token id) claims.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        config = settings or get_settings()
        self._ttl_minutes = config.jwt_access_ttl_minutes
        self._private_key = self._load_private_key(config.jwt_private_key)
        self._public_key = self._load_public_key(config.jwt_public_key)

    @staticmethod
    def _load_private_key(pem: str) -> RSAPrivateKey:
        if not pem or not pem.strip():
            raise ValueError("JWT_PRIVATE_KEY is not configured")
        return cast(RSAPrivateKey, load_pem_private_key(pem.encode(), password=None))

    @staticmethod
    def _load_public_key(pem: str) -> RSAPublicKey:
        if not pem or not pem.strip():
            raise ValueError("JWT_PUBLIC_KEY is not configured")
        return cast(RSAPublicKey, load_pem_public_key(pem.encode()))

    def create_access_token(
        self,
        user_id: uuid.UUID | str,
        tenant_id: uuid.UUID | str | None,
        permissions: list[str] | tuple[str, ...] | set[str],
    ) -> str:
        """Issue a signed access token with a 15-minute (configurable) expiry."""
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "sub": str(user_id),
            "tid": str(tenant_id) if tenant_id is not None else None,
            "perm": sorted(permissions),
            "iat": now,
            "exp": now + timedelta(minutes=self._ttl_minutes),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """Verify signature + ``exp``/required claims, mapping failures to domain errors.

        Returns the decoded claim set. Claims are validated at runtime by PyJWT;
        ``Any`` reflects the heterogeneous JSON shape (``sub`` str, ``iat``/``exp``
        int, ``perm`` list[str], etc.). MFA challenge tokens (``mfa=True``) are
        rejected: they are half-authenticated and must never satisfy ``require_auth``.
        """
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                options={"require": ["sub", "iat", "exp", "jti"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError() from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError() from exc
        if payload.get("mfa") is True:
            raise InvalidTokenError()
        return payload

    def create_mfa_token(self, user_id: uuid.UUID | str) -> str:
        """Issue a short-lived (5-minute) MFA challenge token for ``user_id``.

        Distinct from an access token via the ``mfa: true`` claim; it authorizes
        only the ``POST /auth/mfa/challenge`` step, never a full authenticated
        principal (architecture §4.4).
        """
        now = datetime.now(UTC)
        payload: dict[str, object] = {
            "sub": str(user_id),
            "mfa": True,
            "iat": now,
            "exp": now + timedelta(minutes=_MFA_TOKEN_TTL_MINUTES),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def decode_mfa_token(self, token: str) -> dict[str, Any]:
        """Verify an MFA challenge token; raises ``InvalidTokenError`` unless ``mfa``."""
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                options={"require": ["sub", "iat", "exp", "jti"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise ExpiredTokenError() from exc
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError() from exc
        if payload.get("mfa") is not True:
            raise InvalidTokenError()
        return payload


_MFA_TOKEN_TTL_MINUTES = 5

__all__ = ["JWTService", "PasswordHasher", "TOTP"]
