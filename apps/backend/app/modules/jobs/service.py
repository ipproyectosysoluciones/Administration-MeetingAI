"""Jobs service: enqueue/dequeue/lifecycle helpers (TASK-253).

SKIP-LOCKED claim pattern: one worker claims exactly one pending job.
Retry path re-resets to pending with exponential backoff or marks failed permanently.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import APIError
from app.modules.recordings.models import Job

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

    async def claim_next(self, session: AsyncSession, worker_id: str) -> Job | None:
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
    ) -> list[Job]:
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
