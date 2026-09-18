"""Cross-tenant isolation suite (TASK-090).

Two-tenant fixture plus small helpers. Mirrors the users/audit conftest pattern:
real FastAPI app against the Docker PostgreSQL test database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app
from tests.integration.audit.conftest import api, register_admin

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


@dataclass
class Tenant:
    """A registered organization + its org-admin credentials and resource ids."""

    token: str
    org_id: str
    user_id: str
    email: str
    password: str
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class TwoTenants:
    a: Tenant
    b: Tenant


@pytest.fixture
async def two_tenants(app: FastAPI) -> TwoTenants:
    """Register two fully independent organizations (tenants A and B)."""
    a = await register_admin(app)
    b = await register_admin(app)
    tenant_a = Tenant(
        token=a["access_token"],
        org_id=a["user"]["tenant_id"],
        user_id=a["user"]["id"],
        email=a["user"]["email"],
        password="securePassword123",
    )
    tenant_b = Tenant(
        token=b["access_token"],
        org_id=b["user"]["tenant_id"],
        user_id=b["user"]["id"],
        email=b["user"]["email"],
        password="securePassword123",
    )
    assert tenant_a.org_id != tenant_b.org_id
    return TwoTenants(a=tenant_a, b=tenant_b)


async def create_property(app: FastAPI, tenant: Tenant, name: str) -> str:
    resp = await api(
        app,
        "POST",
        "/api/v1/organizations/me/properties",
        json={"name": name},
        token=tenant.token,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def list_resource_id(app: FastAPI, tenant: Tenant, path: str) -> str:
    """Fetch the first resource id from a tenant-scoped list endpoint."""
    resp = await api(app, "GET", path, token=tenant.token)
    assert resp.status_code == 200, resp.text
    items = resp.json().get("items") or resp.json().get("roles") or resp.json()
    if isinstance(items, dict):  # properties: {"items": [...]}
        items = items["items"]
    assert items, f"no items at {path}"
    return str(items[0]["id"])


__all__ = [
    "Tenant",
    "TwoTenants",
    "api",
    "create_property",
    "list_resource_id",
    "register_admin",
    "uuid",
    "pytest",
    "FastAPI",
    "async_sessionmaker",
]
