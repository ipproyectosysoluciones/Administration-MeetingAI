"""Integration: TranscriptionService against real PostgreSQL (TASK-302).

Covers tenant-scoped persistence of drafts, JSONB segments round-trip, and
the partial unique index (one active draft per recording) behavior.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.meetings.models import Meeting
from app.modules.organizations.models import Organization
from app.modules.recordings.models import Recording
from app.modules.transcription.provider import Segment, TranscriptionResult
from app.modules.transcription.service import TranscriptionService
from app.modules.users.models import User


async def _seed_recording(factory) -> Recording:
    async with factory() as session:
        org = Organization(name=f"Org {uuid.uuid4()}", slug=f"org-{uuid.uuid4().hex[:8]}")
        session.add(org)
        await session.flush()
        user = User(
            email=f"u-{uuid.uuid4().hex[:8]}@test.dev",
            password_hash="x",
            full_name="U",
        )
        session.add(user)
        await session.flush()
        meeting = Meeting(
            organization_id=org.id,
            title="Junta",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        session.add(meeting)
        await session.flush()
        recording = Recording(
            meeting_id=meeting.id,
            tenant_id=org.id,
            filename="a.mp3",
            content_type="audio/mpeg",
            size_bytes=10,
            sha256="0" * 64,
            storage_path=f"{org.id}/{meeting.id}/{uuid.uuid4()}",
            uploaded_by=user.id,
        )
        session.add(recording)
        await session.commit()
        return recording


def _result() -> TranscriptionResult:
    return TranscriptionResult(
        text="Hola mundo",
        segments=[Segment(start=0.0, end=1.5, text="Hola", speaker=None)],
        avg_confidence=0.9,
        language="es",
    )


async def test_create_draft_persists_and_roundtrips(migrated_engine: AsyncEngine) -> None:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    recording = await _seed_recording(factory)
    svc = TranscriptionService()

    async with factory() as session:
        t = await svc.create_draft(
            session,
            recording=recording,
            result=_result(),
            job_id=None,
            model_used="small",
        )
        await session.commit()
        assert t.id is not None
        assert t.status == "draft"
        assert t.segments == [{"start": 0.0, "end": 1.5, "text": "Hola", "speaker": None}]
        assert t.avg_confidence is not None
        assert float(t.avg_confidence) == pytest.approx(0.9)

    async with factory() as session:
        again = await svc.get_active_draft(session, recording.id)
        assert again is not None
        assert again.id == t.id
        assert again.tenant_id == recording.tenant_id


async def test_partial_unique_index_blocks_second_active_draft(
    migrated_engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    recording = await _seed_recording(factory)
    svc = TranscriptionService()

    async with factory() as session:
        await svc.create_draft(
            session,
            recording=recording,
            result=_result(),
            job_id=None,
            model_used="small",
        )
        await session.commit()

    async with factory() as session:
        with pytest.raises(IntegrityError):
            await svc.create_draft(
                session,
                recording=recording,
                result=_result(),
                job_id=None,
                model_used="small",
            )
        await session.rollback()


async def test_new_draft_allowed_after_first_is_final(migrated_engine: AsyncEngine) -> None:
    """A final transcript frees the unique slot; a retry may create a new draft."""
    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)
    recording = await _seed_recording(factory)
    svc = TranscriptionService()

    async with factory() as session:
        t = await svc.create_draft(
            session,
            recording=recording,
            result=_result(),
            job_id=None,
            model_used="small",
        )
        await session.commit()
        t.status = "final"
        await session.commit()

    async with factory() as session:
        t2 = await svc.create_draft(
            session,
            recording=recording,
            result=_result(),
            job_id=None,
            model_used="small",
        )
        await session.commit()
        assert t2.id != t.id
        assert t2.status == "draft"
