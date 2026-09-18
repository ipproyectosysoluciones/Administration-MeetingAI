"""TASK-111: super-admin bootstrap CLI integration test.

Runs the real ``bootstrap_superadmin`` against the Docker PostgreSQL test database
(migrated schema, recreated per test session). Single test because the append-only
audit trigger and FK constraints make cleanup impossible by design.
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


async def test_bootstrap_creates_superadmin_with_audit_then_is_idempotent(
    session_factory,
) -> None:
    # First run: creates the platform super-admin and one audited event.
    async with session_factory() as session:
        user_id, created = await bootstrap_superadmin(
            session, email="root@platform.local", password="bootstrap-pass-123", full_name="Root"
        )
    assert created is True
    assert user_id is not None

    async with session_factory() as session:
        user = (
            await session.execute(select(User).where(User.email == "root@platform.local"))
        ).scalar_one()
        assert user.is_super_admin is True
        assert user.is_active is True

        events = (
            await session.execute(
                select(AuditEvent).where(AuditEvent.action == "platform.super_admin.bootstrap")
            )
        ).scalars().all()
        assert len(events) == 1
        assert events[0].actor_user_id == user.id
        assert events[0].resource_id == user.id

    # Second run: strict no-op — same user count, no new audit row, exit unchanged.
    async with session_factory() as session:
        again_id, created_again = await bootstrap_superadmin(
            session, email="other@platform.local", password="other-pass-123", full_name="Other"
        )
    assert created_again is False
    assert again_id is None

    async with session_factory() as session:
        superadmin_count = (
            await session.execute(
                select(func.count(User.id)).where(User.is_super_admin.is_(True))
            )
        ).scalar_one()
        assert superadmin_count == 1

        event_count = (
            await session.execute(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.action == "platform.super_admin.bootstrap"
                )
            )
        ).scalar_one()
        assert event_count == 1
