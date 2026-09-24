"""TranscriptionService: draft persistence for the transcription pipeline (TASK-302).

Tenant scoping is inherited from the Recording row; the worker never accepts
tenant_id from outside.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recordings.models import Recording
from app.modules.transcription.models import Transcript
from app.modules.transcription.provider import TranscriptionResult


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
        await session.commit()
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
        """Persist a failed transcript row (permanent errors only; see worker)."""
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
        await session.commit()
        return t
