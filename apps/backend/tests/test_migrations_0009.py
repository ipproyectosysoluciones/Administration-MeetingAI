"""MIN-100: migration 0009 — minutes table + minutes.* permissions."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.rbac.models import Permission

_TEST_URL = "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"


async def test_minutes_permissions_seeded(migrated_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    async with factory() as session:
        stmt = select(Permission.name).where(Permission.resource == "minutes")
        names = set((await session.execute(stmt)).scalars())
        assert {
            "minutes.read",
            "minutes.write",
            "minutes.approve",
            "minutes.publish",
        } <= names
        total = (
            await session.execute(
                select(func.count()).select_from(Permission).where(Permission.resource == "minutes")
            )
        ).scalar_one()
        assert total == 4
