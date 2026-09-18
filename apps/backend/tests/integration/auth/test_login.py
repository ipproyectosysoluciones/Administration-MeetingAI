"""TASK-041: POST /auth/login — Argon2id verify, token issuance, MFA gate hook.

Integration tests against PostgreSQL. Covers happy path, wrong password (401),
inactive user (403), the MFA-required hook, and audit event capture.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.audit.models import AuditEvent
from app.modules.rbac.models import Role, UserRole
from app.modules.users.models import User


def _payload(**overrides: str) -> dict[str, str]:
    payload: dict[str, str] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Juan Pérez",
        "organization_name": "Conjunto Residencial Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    return payload


async def _post(app: FastAPI, path: str, json: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=json)


async def _register(app: FastAPI, payload: dict[str, str]) -> httpx.Response:
    return await _post(app, "/api/v1/auth/register", payload)


async def _login(app: FastAPI, email: str, password: str) -> httpx.Response:
    return await _post(app, "/api/v1/auth/login", {"email": email, "password": password})


async def _set_user_flags(
    session_factory: async_sessionmaker, email: str, **updates: object
) -> None:
    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        for key, value in updates.items():
            setattr(user, key, value)
        await session.commit()


async def _demote_to_resident(
    session_factory: async_sessionmaker, user_id: uuid.UUID, organization_id: uuid.UUID
) -> None:
    """Replace role assignments with the non-admin ``resident`` base role."""
    async with session_factory() as session:
        resident_role_id = (
            await session.execute(
                select(Role.id).where(Role.name == "resident", Role.organization_id.is_(None))
            )
        ).scalar_one()
        await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
        session.add(
            UserRole(user_id=user_id, role_id=resident_role_id, organization_id=organization_id)
        )
        await session.commit()


async def test_login_returns_tokens_for_non_admin_without_mfa(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    """A non-administrative user logs in without MFA; admins are gated (TASK-046)."""
    payload = _payload()
    reg = await _register(auth_app, payload)
    await _demote_to_resident(
        session_factory,
        uuid.UUID(reg.json()["user"]["id"]),
        uuid.UUID(reg.json()["user"]["tenant_id"]),
    )

    resp = await _login(auth_app, payload["email"], payload["password"])

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["mfa_required"] is False
    assert body["user"]["email"] == payload["email"]
    assert "organization.read" in body["user"]["permissions"]
    assert "refresh_token" in resp.cookies


async def test_login_rejects_wrong_password(auth_app: FastAPI) -> None:
    payload = _payload()
    await _register(auth_app, payload)

    resp = await _login(auth_app, payload["email"], "wrong-password")

    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"
    assert "access_token" not in resp.json()


async def test_login_rejects_inactive_user(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    payload = _payload()
    await _register(auth_app, payload)
    await _set_user_flags(session_factory, payload["email"], is_active=False)

    resp = await _login(auth_app, payload["email"], payload["password"])

    assert resp.status_code == 403
    assert resp.json()["code"] == "USER_INACTIVE"


async def test_login_returns_mfa_required_when_enrolled(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    payload = _payload()
    await _register(auth_app, payload)
    await _set_user_flags(session_factory, payload["email"], mfa_enabled=True)

    resp = await _login(auth_app, payload["email"], payload["password"])

    assert resp.status_code == 200, resp.text
    assert resp.json()["mfa_required"] is True
    assert "access_token" not in resp.json()


async def test_login_writes_audit_event(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    payload = _payload()
    reg = await _register(auth_app, payload)
    user_id = reg.json()["user"]["id"]
    await _demote_to_resident(
        session_factory,
        uuid.UUID(user_id),
        uuid.UUID(reg.json()["user"]["tenant_id"]),
    )

    resp = await _login(auth_app, payload["email"], payload["password"])
    assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        events = (
            (await session.execute(select(AuditEvent).where(AuditEvent.action == "auth.login")))
            .scalars()
            .all()
        )
        assert any(e.actor_user_id == uuid.UUID(user_id) for e in events)
