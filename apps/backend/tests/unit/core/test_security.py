"""Unit tests for core security primitives (TASK-020 / TASK-021).

TASK-020 — Argon2id password hashing service.
TASK-021 — RS256 JWT service (15-minute access tokens).

Test priority (reunionai-tdd-standards): these are domain/security primitives.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.core.security import JWTService, PasswordHasher


@pytest.fixture
def hasher() -> PasswordHasher:
    return PasswordHasher(Settings())


# ---------------------------------------------------------------------------
# TASK-020 — password hashing service (Argon2id)
# ---------------------------------------------------------------------------
class TestPasswordHasher:
    def test_hash_and_verify_roundtrip(self, hasher: PasswordHasher) -> None:
        digest = hasher.hash("correct horse battery staple")
        assert digest != "correct horse battery staple"
        assert hasher.verify("correct horse battery staple", digest) is True

    def test_verify_wrong_password_rejected(self, hasher: PasswordHasher) -> None:
        digest = hasher.hash("correct horse battery staple")
        assert hasher.verify("wrong password", digest) is False

    def test_verify_rejects_malformed_hash(self, hasher: PasswordHasher) -> None:
        assert hasher.verify("anything", "not-a-valid-argon2-hash") is False

    def test_hash_is_salted_and_unique(self, hasher: PasswordHasher) -> None:
        password = "same password"
        assert hasher.hash(password) != hasher.hash(password)

    def test_argon2id_parameters(self, hasher: PasswordHasher) -> None:
        """Parameters must match architecture.md §4.3 (OWASP-tuned)."""
        digest = hasher.hash("parameters check")
        # $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
        parts = digest.split("$")
        assert parts[1] == "argon2id"
        params = parts[3]
        assert "m=65536" in params
        assert "t=3" in params
        assert "p=4" in params

    def test_needs_rehash_flags_stale_parameters(self) -> None:
        from argon2 import PasswordHasher as Argon2Hasher

        # A digest produced with weak parameters must be flagged for rehash.
        weak = Argon2Hasher(time_cost=1, memory_cost=4096, parallelism=1)
        stale_digest = weak.hash("rehash me")
        assert PasswordHasher(Settings()).needs_rehash(stale_digest) is True

    def test_needs_rehash_false_for_current_parameters(self, hasher: PasswordHasher) -> None:
        assert hasher.needs_rehash(hasher.hash("fresh")) is False

    def test_verify_is_not_free(self, hasher: PasswordHasher) -> None:
        """Timing sanity: verification must incur the memory-hard Argon2 cost.

        A trivial String comparison short-circuits in microseconds; Argon2id at
        §4.3 parameters takes tens of milliseconds. A lenient floor guards against
        accidental regression to a plain-compare implementation without being flaky.
        """
        digest = hasher.hash("timing password")
        start = time.perf_counter()
        hasher.verify("wrong", digest)
        elapsed_s = time.perf_counter() - start
        assert elapsed_s >= 0.005, f"verification completed too fast ({elapsed_s:.6f}s)"

    # ---------------------------------------------------------------------------
    # TASK-021 — JWT service (RS256, 15-minute access tokens)
    # ---------------------------------------------------------------------------
    class TestJWTService:
        @pytest.fixture
        def svc(self, rsa_keys: tuple[str, str]) -> JWTService:
            private_pem, public_pem = rsa_keys
            return JWTService(Settings(jwt_private_key=private_pem, jwt_public_key=public_pem))

        def test_sign_and_verify_roundtrip(self, svc: JWTService) -> None:
            user_id = uuid.uuid4()
            tenant_id = uuid.uuid4()
            permissions = ["user.read", "meeting.read"]
            token = svc.create_access_token(user_id, tenant_id, permissions)
            payload = svc.decode_access_token(token)
            assert payload["sub"] == str(user_id)
            assert payload["tid"] == str(tenant_id)
            assert set(payload["perm"]) == set(permissions)

        def test_claims_present(self, svc: JWTService) -> None:
            token = svc.create_access_token(uuid.uuid4(), uuid.uuid4(), ["organization.read"])
            payload = svc.decode_access_token(token)
            for claim in ("sub", "tid", "perm", "iat", "exp", "jti"):
                assert claim in payload, f"missing claim {claim}"

        def test_expiry_is_15_minutes(self, svc: JWTService) -> None:
            token = svc.create_access_token(uuid.uuid4(), uuid.uuid4(), [])
            payload = svc.decode_access_token(token)
            assert payload["exp"] - payload["iat"] == 15 * 60

        def test_expired_token_rejected(self, svc: JWTService, rsa_keys: tuple[str, str]) -> None:
            private_pem, _ = rsa_keys
            now = datetime.now(UTC)
            expired = jwt.encode(
                {
                    "sub": str(uuid.uuid4()),
                    "tid": None,
                    "perm": [],
                    "iat": now - timedelta(minutes=30),
                    "exp": now - timedelta(minutes=15),
                    "jti": str(uuid.uuid4()),
                },
                private_pem,
                algorithm="RS256",
            )
            with pytest.raises(ExpiredTokenError):
                svc.decode_access_token(expired)

        def test_wrong_key_rejected(
            self, rsa_keys: tuple[str, str], rsa_keys_other: tuple[str, str]
        ) -> None:
            private_pem, public_pem = rsa_keys
            other_private, _other_public = rsa_keys_other
            token = jwt.encode(
                {"sub": str(uuid.uuid4()), "iat": 0, "exp": 2**31},
                other_private,
                algorithm="RS256",
            )
            svc = JWTService(Settings(jwt_private_key=private_pem, jwt_public_key=public_pem))
            with pytest.raises(InvalidTokenError):
                svc.decode_access_token(token)

        def test_tampered_token_rejected(self, svc: JWTService) -> None:
            token = svc.create_access_token(uuid.uuid4(), uuid.uuid4(), ["user.read"])
            header, payload, signature = token.split(".")
            tampered_payload = jwt.utils.base64url_encode(b'{"sub": "attacker"}').decode()
            tampered = f"{header}.{tampered_payload}.{signature}"
            with pytest.raises(InvalidTokenError):
                svc.decode_access_token(tampered)

        def test_missing_key_raises_configuration_error(self) -> None:
            with pytest.raises(ValueError):
                JWTService(Settings())
