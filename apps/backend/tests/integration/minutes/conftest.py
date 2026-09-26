"""Fixtures for minutes-module integration tests (MIN-103).

Mirrors the meetings/users conftest: real FastAPI app + migrated PostgreSQL test DB
+ ephemeral RS256 keypair.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app
from app.modules.meetings.models import Meeting

TEST_DATABASE_URL = "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"


@pytest.fixture(scope="session")
def engine(migrated_engine: AsyncEngine) -> AsyncEngine:
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def settings(rsa_keys: tuple[str, str]) -> Settings:
    private_pem, public_pem = rsa_keys
    return Settings(
        database_url=TEST_DATABASE_URL,
        jwt_private_key=private_pem,
        jwt_public_key=public_pem,
    )


@pytest.fixture
def app(settings: Settings, session_factory: async_sessionmaker) -> FastAPI:
    return create_app(settings=settings, session_factory=session_factory)


async def api(
    app: FastAPI,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
    token: str | None = None,
) -> httpx.Response:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", headers=headers
    ) as client:
        return await client.request(method, path, json=json)


async def register_admin(app: FastAPI, **overrides: object) -> dict[str, Any]:
    payload: dict[str, object] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Org Admin",
        "organization_name": "Conjunto Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    resp = await api(app, "POST", "/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return dict(resp.json())


async def seed_meeting(
    session_factory: async_sessionmaker, organization_id: uuid.UUID
) -> uuid.UUID:
    """Insert a meeting directly into ``organization_id``; returns its id."""
    async with session_factory() as session:
        meeting = Meeting(
            organization_id=organization_id,
            title="Junta ordinaria",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        session.add(meeting)
        await session.commit()
        return meeting.id
