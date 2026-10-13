"""Jobs service: enqueue/dequeue/lifecycle helpers (TASK-253).

SKIP-LOCKED claim pattern: one worker claims exactly one pending job.
Retry path re-resets to pending with exponential backoff or marks failed permanently.

Job Types:
- process_recording: audio/video processing
- transcribe_audio: Speech-to-Text (faster-whisper)
- process_ocr: OCR processing (Tesseract/OCRmyPDF)
- ai_process_meeting: AI summarization (decisions, tasks, summary)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.recordings.models import Job

# Job type constants
JOB_TYPE_TRANSCRIBE = "transcribe_audio"
JOB_TYPE_OCR = "process_ocr"
JOB_TYPE_AI_PROCESS = "ai_process_meeting"
JOB_TYPE_PROCESS_RECORDING = "process_recording"

_WAITING_STATUSES = ("pending",)


class JobService:
    """Generic job queue service for worker processes."""

    async def enqueue(
        self,
        session: AsyncSession,
        *,
        type: str,
        payload: dict[str, Any],
        run_at: datetime | None = None,
        max_attempts: int = 5,
    ) -> Job:
        job = Job(
            type=type,
            payload=payload,
            max_attempts=max_attempts,
            status="pending",
            run_at=run_at or datetime.now(UTC),
        )
        session.add(job)
        await session.flush()
        return job

    # Convenience methods for specific job types
    async def enqueue_transcription(
        self,
        session: AsyncSession,
        *,
        recording_id: str,
        meeting_id: str | None,
        language: str = "es",
        diarize: bool = True,
        run_at: datetime | None = None,
    ):
        return await self.enqueue(
            session,
            type="transcribe_audio",
            payload={
                "recording_id": recording_id,
                "meeting_id": meeting_id,
                "language": language,
                "diarize": diarize,
            },
            run_at=run_at,
        )

    async def enqueue_ocr(
        self,
        session: AsyncSession,
        *,
        document_id: str,
        run_at: datetime | None = None,
    ):
        return await self.enqueue(
            session,
            type="process_ocr",
            payload={"document_id": document_id},
            run_at=run_at,
        )

    async def enqueue_ai_processing(
        self,
        session: AsyncSession,
        *,
        meeting_id: str,
        transcription_id: str,
        document_ids: list[str] | None = None,
        run_at: datetime | None = None,
    ):
        return await self.enqueue(
            session,
            type="ai_process_meeting",
            payload={
                "meeting_id": meeting_id,
                "transcription_id": transcription_id,
                "document_ids": document_ids or [],
            },
            run_at=run_at,
        )

    async def claim_next(self, session: AsyncSession, worker_id: str):
        """Claim the oldest due pending job with FOR UPDATE SKIP LOCKED."""
        stmt = (
            select(Job)
            .where(
                and_(
                    Job.status == "pending",
                    Job.run_at <= datetime.now(UTC),
                )
            )
            .order_by(Job.run_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = (await session.execute(stmt)).scalar_one_or_none()
        if job is None:
            return None
        job.status = "running"
        job.locked_by = worker_id
        job.locked_at = datetime.now(UTC)
        job.attempts += 1
        session.add(job)
        return job

    async def claim_batch(
        self, session: AsyncSession, worker_id: str, limit: int = 10
    ) -> list:
        """Claim up to ``limit`` pending jobs with FOR UPDATE SKIP LOCKED."""
        stmt = (
            select(Job)
            .where(
                and_(
                    Job.status == "pending",
                    Job.run_at <= datetime.now(UTC),
                )
            )
            .order_by(Job.run_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list((await session.execute(stmt)).scalars())
        now = datetime.now(UTC)
        for job in jobs:
            job.status = "running"
            job.locked_by = worker_id
            job.locked_at = now
            job.attempts += 1
        session.add_all(jobs)
        return jobs

    async def complete(self, session: AsyncSession, job: Job, worker_id: str) -> None:
        """Mark a claimed job done; requires ownership."""
        self._require_owned(job, worker_id)
        job.status = "done"
        job.completed_at = datetime.now(UTC)
        session.add(job)

    async def fail(self, session: AsyncSession, job: Job, worker_id: str) -> None:
        """Mark a claimed job failed; with remaining attempts it returns to pending with backoff."""
        self._require_owned(job, worker_id)
        if job.attempts >= job.max_attempts:
            job.status = "failed"
        else:
            delay_second = 10 * (2 ** (job.attempts - 1))
            job.status = "pending"
            job.run_at = datetime.now(UTC) + timedelta(seconds=delay_second)
            job.locked_by = None
            job.locked_at = None
        session.add(job)

    @staticmethod
    def _require_owned(job: Job, worker_id: str) -> None:
        if job.locked_by != worker_id:
            raise APIError(409, "JOB_NOT_OWNED", "Job is not claimed by this worker")