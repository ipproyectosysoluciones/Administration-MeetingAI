"""TASK-300: migration 0007 — transcriptions table + transcription.* permissions."""

from __future__ import annotations

from sqlalchemy import MetaData, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.rbac.models import Permission


async def _meta(conn) -> MetaData:
    """Reflect the live database via connection-bound autoload."""

    async def run_sync(sync_conn):
        md = MetaData()
        await sync_conn.run_sync(md.reflect)
        return md

    return await run_sync(conn)


async def test_transcriptions_schema_and_constraints(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        md = await _meta(conn)
        transcriptions = md.tables["transcriptions"]
        col_by_name = {c.name: c for c in transcriptions.columns}
        expected = {
            "id",
            "recording_id",
            "meeting_id",
            "tenant_id",
            "language",
            "text",
            "segments",
            "avg_confidence",
            "model_used",
            "version",
            "status",
            "error",
            "created_by_job_id",
            "created_at",
            "updated_at",
        }
        assert expected <= col_by_name.keys()
        assert col_by_name["recording_id"].nullable is False
        assert col_by_name["meeting_id"].nullable is False
        assert col_by_name["tenant_id"].nullable is False
        assert col_by_name["text"].nullable is False
        assert col_by_name["version"].nullable is False
        assert col_by_name["status"].nullable is False


async def test_transcriptions_indexes_exist(migrated_engine: AsyncEngine) -> None:
    async with migrated_engine.connect() as conn:
        md = await _meta(conn)
        transcriptions = md.tables["transcriptions"]
        index_names = {ix.name for ix in transcriptions.indexes}
        assert {
            "ix_transcripts_recording",
            "ix_transcripts_tenant",
            "ix_transcripts_meeting",
            "ux_transcripts_active_draft",
        } <= index_names


async def test_transcription_permissions_seeded(migrated_engine: AsyncEngine) -> None:
    session_factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    async with session_factory() as session:
        stmt = select(Permission.name).where(Permission.resource == "transcription")
        names = set((await session.execute(stmt)).scalars())
        assert {"transcription.read", "transcription.create", "transcription.retry"} <= names

        total_stmt = (
            select(func.count())
            .select_from(Permission)
            .where(Permission.resource == "transcription")
        )
        total = (await session.execute(total_stmt)).scalar_one()
        assert total == 3
