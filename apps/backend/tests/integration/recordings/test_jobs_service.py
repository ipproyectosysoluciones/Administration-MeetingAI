"""Job service unit tests (TASK-253)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.exceptions import APIError
from app.modules.jobs.service import JobService
from app.modules.recordings.models import Job

TEST_DATABASE_URL = "postgresql+asyncpg://reunionai:reunionai@localhost:5433/reunionai"


@pytest.fixture(scope="session")
def engine(migrated_engine: AsyncEngine) -> AsyncEngine:
    return create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def service() -> JobService:
    return JobService()


async def _create_pending_job(session_factory) -> uuid.UUID:
    """Insert a job (committed) and return its id."""
    async with session_factory() as session:
        job = await JobService().enqueue(
            session,
            type="process_recording",
            payload={"recording_id": str(uuid.uuid4())},
        )
        await session.commit()
        return job.id


async def test_enqueue_and_claim(session_factory, service) -> None:
    job_id = await _create_pending_job(session_factory)
    async with session_factory() as session:
        job = await service.claim_next(session, "worker-1")
        assert job is not None
        assert job.id == job_id
        assert job.status == "running"
        assert job.locked_by == "worker-1"
        assert job.attempts == 1
        await session.commit()


async def test_claim_skips_locked(session_factory, service) -> None:
    """Second claim of the same pending job returns None while worker-1 holds it."""
    await _create_pending_job(session_factory)
    async with session_factory() as s1:
        first = await service.claim_next(s1, "w1")
        assert first is not None, "first claim must succeed for a fresh pending job"
        await s1.commit()
    async with session_factory() as s2:
        second = await service.claim_next(s2, "w2")
        assert second is None


async def test_complete_marks_done(session_factory, service) -> None:
    await _create_pending_job(session_factory)
    async with session_factory() as s:
        job = await service.claim_next(s, "w1")
        await service.complete(s, job, "w1")
        await s.commit()
        assert job.status == "done"
        assert job.completed_at is not None


async def test_fail_resets_pending_with_backoff(session_factory, service) -> None:
    await _create_pending_job(session_factory)
    async with session_factory() as s:
        job = await service.claim_next(s, "w1")
        await service.fail(s, job, "w1")
        await s.commit()
        assert job.status == "pending"  # remaining attempts left
        assert job.run_at > datetime.now(UTC)


async def test_fail_after_max_attempts_terminal(session_factory, service) -> None:
    """Directly set attempts=max-1 on the claimed row and fail it -> terminal failed."""
    await _create_pending_job(session_factory)

    async with session_factory() as s:
        job = await service.claim_next(s, "w1")
        job.attempts = job.max_attempts  # bypass the guard
        await service.fail(s, job, "w1")
        await s.commit()
        assert job.status == "failed"


async def test_fail_without_claim_raises(session_factory, service) -> None:
    async with session_factory() as s:
        ghost = Job(
            id=uuid.uuid4(),
            type="process_recording",
            payload={"x": str(uuid.uuid4())},
            status="running",
            locked_by="another-worker",
        )
        s.add(ghost)
        await s.commit()
        with pytest.raises(APIError):
            await service.fail(s, ghost, worker_id="never-claimed")
