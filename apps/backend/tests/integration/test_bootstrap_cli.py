"""TASK-111: super-admin bootstrap CLI integration test.

Runs the real ``bootstrap_superadmin`` against the Docker PostgreSQL test database
(migrated schema, recreated per session). Other suites already create super-admins,
so assertions are delta-based rather than absolute.
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.cli import bootstrap_superadmin
from app.modules.audit.models import AuditEvent
from app.modules.users.models import User

TEST_DATABASE_URL = "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"


@pytest.fixture
def session_factory(migrated_engine: AsyncEngine) -> async_sessionmaker:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False)


async def _counts(session_factory) -> tuple[int, int]:
    async with session_factory() as session:
        superadmins = (
            await session.execute(
                select(func.count(User.id)).where(User.is_super_admin.is_(True))
            )
        ).scalar_one()
        events = (
            await session.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.action == "platform.super_admin.bootstrap"
                )
            )
        ).scalar_one()
    return superadmins, events


async def test_bootstrap_creates_superadmin_with_audit_then_is_idempotent(
    session_factory,
) -> None:
    superadmins_before, events_before = await _counts(session_factory)

    async with session_factory() as session:
        user_id, created = await bootstrap_superadmin(
            session, email="root@platform.local", password="bootstrap-pass-123", full_name="Root"
        )

    if superadmins_before == 0:
        # First-ever bootstrap: user created + exactly one new audit event.
        assert created is True
        assert user_id is not None
        superadmins_mid, events_mid = await _counts(session_factory)
        assert superadmins_mid == 1
        assert events_mid == events_before + 1

        async with session_factory() as session:
            user = (
                await session.execute(select(User).where(User.email == "root@platform.local"))
            ).scalar_one()
            assert user.is_super_admin is True
    else:
        # A super-admin already exists (created by another suite): strict no-op.
        assert created is False
        assert user_id is None

    # Second call is always a no-op, regardless of the starting state.
    async with session_factory() as session:
        again_id, created_again = await bootstrap_superadmin(
            session, email="other@platform.local", password="other-pass-123", full_name="Other"
        )
    assert created_again is False
    assert again_id is None

    superadmins_after, events_after = await _counts(session_factory)
    expected_superadmins = superadmins_before + (1 if superadmins_before == 0 else 0)
    expected_events = events_before + (1 if superadmins_before == 0 else 0)
    assert superadmins_after == expected_superadmins
    assert events_after == expected_events
