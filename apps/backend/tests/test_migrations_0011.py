"""OCR-200: migration 0011 — ocr_jobs table + document.*/ocr.* permissions."""

from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.rbac.models import Permission

_OCR_PERMISSIONS = {
    "document.read",
    "document.upload",
    "document.download",
    "document.update",
    "document.delete",
    "ocr.run",
    "ocr.read",
    "ocr.correct",
}


async def test_ocr_jobs_table_exists(migrated_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    async with factory() as session:
        table = (await session.execute(text("SELECT to_regclass('public.ocr_jobs')"))).scalar_one()
        assert table == "ocr_jobs"
        # PRD §27 states are enforced by a CHECK constraint. Matched by
        # definition substrings, not by name: env.py's naming convention
        # completes explicit constraint names, and PostgreSQL normalizes
        # IN-lists to = ANY(ARRAY[...]) — both make name/literal coupling brittle.
        status_checks = (
            await session.execute(
                text(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conrelid = 'public.ocr_jobs'::regclass "
                    "AND contype = 'c' "
                    "AND pg_get_constraintdef(oid) LIKE '%status%' "
                    "AND pg_get_constraintdef(oid) LIKE '%queued%' "
                    "AND pg_get_constraintdef(oid) LIKE '%failed%'"
                )
            )
        ).scalar_one()
        assert status_checks == 1
        # One attempt row per document attempt number.
        unique_attempt = (
            await session.execute(
                text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE tablename = 'ocr_jobs' "
                    "AND indexdef LIKE '%UNIQUE%' "
                    "AND indexdef LIKE '%document_id%' "
                    "AND indexdef LIKE '%attempt%'"
                )
            )
        ).scalar_one()
        assert unique_attempt == 1


async def test_ocr_permissions_seeded(migrated_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    async with factory() as session:
        names = set(
            (
                await session.execute(
                    select(Permission.name).where(Permission.resource.in_(("document", "ocr")))
                )
            )
            .scalars()
            .all()
        )
        assert _OCR_PERMISSIONS <= names
        total = (
            await session.execute(
                select(func.count())
                .select_from(Permission)
                .where(Permission.resource.in_(("document", "ocr")))
            )
        ).scalar_one()
        assert total == len(_OCR_PERMISSIONS)
