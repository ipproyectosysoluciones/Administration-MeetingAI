"""TranscriptionService: draft persistence for the transcription pipeline (TASK-302).

Tenant scoping is inherited from the Recording row; the worker never accepts
tenant_id from outside.
"""

from __future__ import annotations

import math
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.recordings.models import Recording
from app.modules.transcription.models import Transcript
from app.modules.transcription.provider import TranscriptionResult
from app.modules.transcription.schemas import TranscriptionListResponse, TranscriptionResponse


class TranscriptionService:
    async def get_active_draft(
        self, session: AsyncSession, recording_id: uuid.UUID
    ) -> Transcript | None:
        """Return the active (status='draft') transcript for a recording, if any."""
        stmt = select(Transcript).where(
            Transcript.recording_id == recording_id, Transcript.status == "draft"
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def create_draft(
        self,
        session: AsyncSession,
        *,
        recording: Recording,
        result: TranscriptionResult,
        job_id: uuid.UUID | None,
        model_used: str,
    ) -> Transcript:
        """Insert the draft row (flush only); the caller owns commit."""
        t = Transcript(
            recording_id=recording.id,
            meeting_id=recording.meeting_id,
            tenant_id=recording.tenant_id,
            language=result.language or "es",
            text=result.text,
            segments=[
                {"start": s.start, "end": s.end, "text": s.text, "speaker": s.speaker}
                for s in result.segments
            ],
            avg_confidence=(
                Decimal(str(result.avg_confidence)) if result.avg_confidence is not None else None
            ),
            model_used=model_used,
            version=1,
            status="draft",
            error=None,
            created_by_job_id=job_id,
        )
        session.add(t)
        await session.flush()
        return t

    async def mark_failed(
        self,
        session: AsyncSession,
        *,
        recording: Recording,
        job_id: uuid.UUID | None,
        error: str,
        model_used: str,
    ) -> Transcript:
        """Insert a failed transcript row (flush only); the caller owns commit."""
        t = Transcript(
            recording_id=recording.id,
            meeting_id=recording.meeting_id,
            tenant_id=recording.tenant_id,
            language=None,
            text="",
            segments=[],
            avg_confidence=None,
            model_used=model_used,
            version=1,
            status="failed",
            error=error,
            created_by_job_id=job_id,
        )
        session.add(t)
        await session.flush()
        return t

    # -- read-only REST surface (TASK-304) ------------------------------------

    async def get(
        self, session: AsyncSession, *, transcription_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Transcript:
        stmt = select(Transcript).where(
            Transcript.id == transcription_id, Transcript.tenant_id == tenant_id
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            # 404 (not 403): never leak existence across tenants.
            raise APIError(404, "TRANSCRIPTION_NOT_FOUND", "Transcription not found")
        return row

    async def list_for_recording(
        self,
        session: AsyncSession,
        *,
        recording_id: uuid.UUID,
        tenant_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> TranscriptionListResponse:
        recording = (
            await session.execute(
                select(Recording).where(
                    Recording.id == recording_id,
                    Recording.tenant_id == tenant_id,
                    Recording.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if recording is None:
            raise APIError(404, "RECORDING_NOT_FOUND", "Recording not found")

        base = select(Transcript).where(Transcript.recording_id == recording_id)
        total = (
            await session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            (
                await session.execute(
                    base.order_by(Transcript.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .scalars()
            .all()
        )
        return TranscriptionListResponse(
            items=[TranscriptionResponse.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total else 1,
        )
