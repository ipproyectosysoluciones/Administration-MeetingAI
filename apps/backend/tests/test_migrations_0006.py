"""TASK-250: migration 0006 — recordings + jobs, recording.* permissions."""

from __future__ import annotations

from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.ext.asyncio import AsyncEngine


async def _meta(conn) -> MetaData:
    """Reflect the live database via connection-bound autoload."""

    async def run_sync(sync_conn):
        md = MetaData()
        await sync_conn.run_sync(md.reflect)
        return md

    return await run_sync(conn)


async def test_recordings_schema_and_constraints(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        md = await _meta(conn)
        recordings = md.tables["recordings"]
        col_by_name = {c.name: c for c in recordings.columns}
        expected = {
            "id", "meeting_id", "tenant_id", "filename", "size_bytes", "sha256",
            "storage_path", "duration_seconds", "status", "deleted_at",
        }
        assert expected <= col_by_name.keys()
        assert col_by_name["meeting_id"].nullable is False
        assert col_by_name["tenant_id"].nullable is False

        check_names = {c.name for c in recordings.constraints}
        assert any("status" in n for n in check_names)


async def test_jobs_table_structure(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        md = await _meta(conn)
        jobs = md.tables["jobs"]
        cols = {c.name for c in jobs.columns}
        expected = {
            "id", "type", "payload", "status", "attempts", "max_attempts",
            "run_at", "locked_by", "locked_at", "completed_at",
            "created_at", "updated_at",
        }
        assert expected <= cols


async def test_recording_permissions_seeded(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        md = await _meta(conn)
        permissions = Table("permissions", md)
        perms_stmt = select(permissions.c.name).where(permissions.c.resource == "recording")
        names = set((await conn.execute(perms_stmt)).scalars())
        assert {"recording.upload", "recording.read", "recording.delete"} <= names

        count_stmt = select(func.count()).select_from(permissions).where(
            permissions.c.resource == "recording"
        )
        assert (await conn.execute(count_stmt)).scalar_one() == 3
