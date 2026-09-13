"""TASK-043: POST /auth/revoke + logout — session revocation.

Integration tests against PostgreSQL. Covers the happy path (revoke → the
refresh token no longer works), the auth requirement (401 without a bearer
token), and audit capture.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.audit.models import AuditEvent


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


async def test_revoke_invalidates_refresh_token(auth_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=_payload())
        assert reg.status_code == 201
        access = reg.json()["access_token"]
        old_refresh = reg.cookies["refresh_token"]

        revoke = await client.post(
            "/api/v1/auth/revoke", headers={"Authorization": f"Bearer {access}"}
        )
        assert revoke.status_code == 200, revoke.text
        assert revoke.json() == {"message": "Session revoked successfully"}

        # Subsequent refresh with the revoked token fails.
        refresh = await client.post(
            "/api/v1/auth/refresh", cookies={"refresh_token": old_refresh}
        )
        assert refresh.status_code == 401


async def test_revoke_requires_authentication(auth_app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=_payload())
        assert reg.status_code == 201

        # No Authorization header → 401 even though a refresh cookie is present.
        resp = await client.post("/api/v1/auth/revoke")
        assert resp.status_code == 401


async def test_revoke_writes_audit_event(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.post("/api/v1/auth/register", json=_payload())
        access = reg.json()["access_token"]
        user_id = reg.json()["user"]["id"]

        resp = await client.post(
            "/api/v1/auth/revoke", headers={"Authorization": f"Bearer {access}"}
        )
        assert resp.status_code == 200

    async with session_factory() as session:
        events = (
            await session.execute(select(AuditEvent).where(AuditEvent.action == "auth.revoke"))
        ).scalars().all()
        assert any(e.actor_user_id == uuid.UUID(user_id) for e in events)