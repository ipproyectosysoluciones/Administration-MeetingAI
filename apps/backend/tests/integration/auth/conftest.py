"""Fixtures for auth integration tests (PR-3a: register/login/refresh/revoke).

These exercise the real FastAPI app against the Docker PostgreSQL test database
(the same ``reunionai-test-pg`` container used by ``tests/test_migrations.py``).
The app is built with the test session factory and an ephemeral RS256 keypair so
``JWTService`` and the DB-backed authorization resolver are fully wired.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.main import create_app

TEST_DATABASE_URL = "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"


@pytest.fixture(scope="session")
def auth_engine(migrated_engine: AsyncEngine) -> AsyncEngine:
    """Async engine bound to the migrated test database (NullPool for per-test isolation)."""
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
def session_factory(auth_engine: AsyncEngine) -> async_sessionmaker:
    """A session factory the app and tests share, bound to the test database."""
    return async_sessionmaker(auth_engine, expire_on_commit=False)


@pytest.fixture
def auth_settings(rsa_keys: tuple[str, str]) -> Settings:
    private_pem, public_pem = rsa_keys
    return Settings(
        database_url=TEST_DATABASE_URL,
        jwt_private_key=private_pem,
        jwt_public_key=public_pem,
    )


@pytest.fixture
def auth_app(auth_settings: Settings, session_factory: async_sessionmaker) -> FastAPI:
    return create_app(settings=auth_settings, session_factory=session_factory)
