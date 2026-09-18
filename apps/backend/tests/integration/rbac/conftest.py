"""Fixtures for rbac-module integration tests (TASK-070).

Same harness as the users/organizations suites: the Docker test PostgreSQL, an
ephemeral RS256 keypair, and the real FastAPI app wired to the DB-backed resolver.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.security import JWTService, PasswordHasher
from app.main import create_app
from app.modules.organizations.models import Membership
from app.modules.rbac.models import Role, UserRole
from app.modules.users.models import User

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


def _register_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Org Admin",
        "organization_name": "Conjunto Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    return payload


async def _request(
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


async def register(app: FastAPI, **overrides: object) -> dict[str, Any]:
    """Register an org + org-admin and return the parsed JSON body."""
    resp = await _request(app, "POST", "/api/v1/auth/register", json=_register_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


async def mint_token(settings: Settings, user_id: uuid.UUID) -> str:
    """Mint an access token for ``user_id`` via the test RS256 keypair."""
    return JWTService(settings).create_access_token(user_id, None, [])


async def create_member(
    session_factory: async_sessionmaker,
    organization_id: uuid.UUID,
    *,
    role: str = "resident",
) -> tuple[uuid.UUID, str]:
    """Insert a tenant member (Membership + UserRole) and return ``(user_id, email)``."""
    email = f"member-{uuid.uuid4()}@example.com"
    hasher = PasswordHasher()
    async with session_factory() as session:
        user = User(
            email=email,
            password_hash=hasher.hash("memberPass123"),
            full_name="Test Member",
        )
        session.add(user)
        await session.flush()
        role_id = (
            await session.execute(
                select(Role.id).where(Role.name == role, Role.organization_id.is_(None))
            )
        ).scalar_one()
        session.add(Membership(user_id=user.id, organization_id=organization_id, role=role))
        session.add(UserRole(user_id=user.id, role_id=role_id, organization_id=organization_id))
        await session.commit()
        return user.id, email


async def permission_id_by_name(app: FastAPI, token: str, name: str) -> str:
    """Resolve a permission id from ``GET /rbac/permissions`` by name."""
    resp = await _request(app, "GET", "/api/v1/rbac/permissions", token=token)
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        if item["name"] == name:
            return item["id"]
    raise AssertionError(f"permission {name!r} not found in registry")
