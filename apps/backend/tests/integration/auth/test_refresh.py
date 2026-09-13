"""TASK-042: POST /auth/refresh — rotation + reuse detection + grace window.

Integration tests against PostgreSQL. Covers rotation, replay (whole chain
revoked → 401 REFRESH_TOKEN_REUSE_DETECTED), the 30-second grace window for
legitimate concurrent refresh, and expired-token rejection.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.auth.models import RefreshToken


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


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def _mutate_token(
    session_factory: async_sessionmaker, raw_token: str, **updates: object
) -> None:
    async with session_factory() as session:
        token = (
            await session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token))
            )
        ).scalar_one()
        for key, value in updates.items():
            setattr(token, key, value)
        await session.commit()


async def _new_client(app: FastAPI) -> tuple[httpx.AsyncClient, dict[str, str], str]:
    payload = _payload()
    transport = httpx.ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201
    return client, payload, resp.cookies["refresh_token"]


async def test_refresh_rotates_token(auth_app: FastAPI) -> None:
    client, _payload, old_refresh = await _new_client(auth_app)
    try:
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200, resp.text
        assert resp.json()["access_token"]
        new_refresh = resp.cookies["refresh_token"]
        assert new_refresh and new_refresh != old_refresh

        # The rotated (new) token still works on a subsequent refresh.
        resp2 = await client.post("/api/v1/auth/refresh")
        assert resp2.status_code == 200
    finally:
        await client.aclose()


async def test_refresh_reuse_detected_revokes_chain(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    client, _payload, old_refresh = await _new_client(auth_app)
    try:
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        new_refresh = resp.cookies["refresh_token"]

        # Age the replayed token past the 30-second grace window, then replay it.
        await _mutate_token(
            session_factory, old_refresh, revoked_at=datetime.now(UTC) - timedelta(seconds=60)
        )
        replay = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
        assert replay.status_code == 401
        assert replay.json()["code"] == "REFRESH_TOKEN_REUSE_DETECTED"

        # The whole chain — including the live sibling — is now revoked.
        sibling = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": new_refresh})
        assert sibling.status_code == 401
    finally:
        await client.aclose()


async def test_refresh_grace_window_allows_legitimate_successor(auth_app: FastAPI) -> None:
    client, _payload, old_refresh = await _new_client(auth_app)
    try:
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200

        # Replaying the just-replaced token within the grace window is permitted.
        retry = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
        assert retry.status_code == 200, retry.text
    finally:
        await client.aclose()


async def test_refresh_expired_token_rejected(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    client, _payload, old_refresh = await _new_client(auth_app)
    try:
        await _mutate_token(
            session_factory, old_refresh, expires_at=datetime.now(UTC) - timedelta(seconds=1)
        )
        resp = await client.post("/api/v1/auth/refresh", cookies={"refresh_token": old_refresh})
        assert resp.status_code == 401
        assert resp.json()["code"] == "INVALID_REFRESH_TOKEN"
    finally:
        await client.aclose()
