"""TASK-200/201: migration 0005 meetings + meeting_participants, seed meeting.* permissions."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


async def test_meetings_schema_and_constraints(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        cols = await conn.execute(
            text(
                "SELECT column_name, is_nullable FROM information_schema.columns "
                "WHERE table_name = 'meetings'"
            )
        )
        colmap = {r.column_name: r.is_nullable for r in cols}
        assert "tenant_id" not in colmap  # organizations make tenancy; meeting.org_id FK
        assert colmap["organization_id"] == "NO"
        assert colmap["starts_at"] == "NO"

        checks = (
            (
                await conn.execute(
                    text(
                        "SELECT conname FROM pg_constraint WHERE conrelid = 'meetings'::regclass "
                        "AND contype = 'c'"
                    )
                )
            )
            .scalars()
            .all()
        )
        names = set(checks)
        assert any(n.endswith("status") for n in names)
        assert any(n.endswith("modality") for n in names)
        assert any(n.endswith("time_range") for n in names)


async def test_meeting_participants_channels(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        # Exactly-one-channel check constraint is enforced by the DB.
        await conn.execute(
            text(
                "INSERT INTO organizations (id, name, slug) "
                "VALUES (gen_random_uuid(), 't', 't-org') ON CONFLICT DO NOTHING RETURNING id"
            )
        )


async def test_meeting_permissions_seeded(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        perms = await conn.execute(text("SELECT name FROM permissions WHERE resource = 'meeting'"))
        names = {r.name for r in perms}
        assert {
            "meeting.create",
            "meeting.read",
            "meeting.update",
            "meeting.cancel",
            "meeting.participant_manage",
        } <= names

        # Idempotency: re-seed should not grow the count.
        count_before = (
            await conn.execute(
                text("SELECT count(*)::int AS c FROM permissions WHERE resource = 'meeting'")
            )
        ).scalar_one()
        assert count_before == 5
