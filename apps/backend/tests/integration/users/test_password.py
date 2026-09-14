"""TASK-050: self-service password change (POST /users/me/password).

Covers Argon2id re-hash, wrong-current-password rejection, the audit event, and the
session-invalidation rule (all refresh tokens revoked on password change).
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import PasswordHasher
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User

from .conftest import _request, register


async def test_change_password_rehashes_and_verifies(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    reg = await register(app)
    token = reg["access_token"]
    user_id = uuid.UUID(reg["user"]["id"])

    resp = await _request(
        app,
        "POST",
        "/api/v1/users/me/password",
        json={"current_password": "securePassword123", "new_password": "NewSecure456"},
        token=token,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "Password changed successfully"

    async with session_factory() as session:
        user = await session.get(User, user_id)
        hasher = PasswordHasher()
        assert user is not None and user.password_hash.startswith("$argon2id$")
        assert hasher.verify("NewSecure456", user.password_hash)
        assert not hasher.verify("securePassword123", user.password_hash)


async def test_change_password_writes_audit_event(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    reg = await register(app)
    token = reg["access_token"]
    user_id = uuid.UUID(reg["user"]["id"])

    resp = await _request(
        app,
        "POST",
        "/api/v1/users/me/password",
        json={"current_password": "securePassword123", "new_password": "NewSecure456"},
        token=token,
    )
    assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        events = (
            (
                await session.execute(
                    select(AuditEvent).where(AuditEvent.action == "user.password.change")
                )
            )
            .scalars()
            .all()
        )
        assert any(e.actor_user_id == user_id for e in events)


async def test_change_password_rejects_wrong_current_password(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(
        app,
        "POST",
        "/api/v1/users/me/password",
        json={"current_password": "wrong-password", "new_password": "NewSecure456"},
        token=token,
    )

    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "INVALID_CURRENT_PASSWORD"


async def test_change_password_revokes_all_sessions(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    reg = await register(app)
    token = reg["access_token"]
    user_id = uuid.UUID(reg["user"]["id"])

    resp = await _request(
        app,
        "POST",
        "/api/v1/users/me/password",
        json={"current_password": "securePassword123", "new_password": "NewSecure456"},
        token=token,
    )
    assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        active = (
            (
                await session.execute(
                    select(RefreshToken).where(
                        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        assert active == []


async def test_change_password_rejects_weak_password(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(
        app,
        "POST",
        "/api/v1/users/me/password",
        json={"current_password": "securePassword123", "new_password": "short"},
        token=token,
    )

    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "WEAK_PASSWORD"
