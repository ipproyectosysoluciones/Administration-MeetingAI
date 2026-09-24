"""Transcription worker loop (TASK-302): claim-next, skip-if-draft, error classes.

Entrypoint: python -m app.modules.transcription.worker

Error policy (see architecture.md):
- Transient (provider/timeout/IO on temp copy) -> job_service.fail (requeued
  with backoff by the job service until max_attempts).
- Permanent (recording row missing, unreadable storage key) -> transcript row
  marked 'failed' AND job_service.fail (no silent drops; retry is a manual
  re-enqueue gated by the transcription.retry permission).
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import uuid
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recordings.models import Recording
from app.modules.recordings.providers import LocalStorageProvider, StorageProvider
from app.modules.transcription.faster_whisper_provider import FasterWhisperProvider
from app.modules.transcription.provider import (
    PermanentTranscriptionError,
    SpeechToTextProvider,
)
from app.modules.transcription.service import TranscriptionService

logger = logging.getLogger(__name__)

JOB_TYPE = "process_recording"
# Hard bound for a single transcription call; overridable for large models.
TRANSCRIBE_TIMEOUT_SECONDS = float(os.environ.get("TRANSCRIBE_TIMEOUT_SECONDS", "1800"))


class RecordingMissingError(Exception):
    """Permanent: the recording row referenced by the job does not exist."""


async def _audio_to_tempfile(storage: StorageProvider, key: str) -> Path:
    """Copy the stored blob into a local temp file (providers may stream).

    On ANY failure the fd, the read handle, and the temp file are all released.
    """
    fd, tmp_name = tempfile.mkstemp(suffix=Path(key).suffix or ".bin")
    handle = None
    try:
        handle = await storage.open_read(key)
        with os.fdopen(fd, "wb") as out:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except BaseException:
        if handle is not None:
            handle.close()
        else:
            os.close(fd)
        os.unlink(tmp_name)
        raise
    handle.close()
    return Path(tmp_name)


async def run_once(
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    job_service,
    provider: SpeechToTextProvider,
    storage: StorageProvider,
    *,
    worker_id: str,
    service: TranscriptionService | None = None,
) -> bool:
    """Process at most one job. Returns True if a job was claimed."""
    svc = service or TranscriptionService()

    # Phase 1: claim (its own session; committed so processing failures can't corrupt it)
    async with session_factory() as session:
        job = await job_service.claim_next(session, worker_id)
        if job is None:
            return False
        await session.commit()

    recording_id_raw = job.payload.get("recording_id")
    model_used = getattr(provider, "model_name", "unknown")

    try:
        recording_pk = uuid.UUID(str(recording_id_raw))
    except (TypeError, ValueError) as exc:
        # Permanent data corruption in the job payload; never retry.
        logger.error("job %s: invalid recording_id payload %r: %s", job.id, recording_id_raw, exc)
        await _fail_job(session_factory, job_service, job, worker_id)
        return True

    # Phase 2: process in a fresh session, isolated from claim state
    async with session_factory() as session:
        recording = await session.get(Recording, recording_pk)
        try:
            if recording is None:
                raise RecordingMissingError(f"recording not found: {recording_id_raw}")

            existing = await svc.get_active_draft(session, recording.id)
            if existing is not None:
                logger.info(
                    "job %s: active draft exists for recording %s; skipping",
                    job.id,
                    recording.id,
                )
                await _complete_job(session_factory, job_service, job, worker_id)
                return True

            audio_path = await _audio_to_tempfile(storage, recording.storage_path)
            try:
                result = await asyncio.wait_for(
                    provider.transcribe(audio_path), timeout=TRANSCRIBE_TIMEOUT_SECONDS
                )
            finally:
                audio_path.unlink(missing_ok=True)

            await svc.create_draft(
                session,
                recording=recording,
                result=result,
                job_id=job.id,
                model_used=model_used,
            )
            await _complete_job(session_factory, job_service, job, worker_id)
            logger.info("job %s: transcription completed for recording %s", job.id, recording.id)
            return True
        except RecordingMissingError as exc:
            # Permanent: no recording row exists, so no failed Transcript can be
            # attached (FK); the job is failed permanently via the job service.
            logger.error("job %s: permanent failure: %s", job.id, exc)
            await _fail_job(session_factory, job_service, job, worker_id)
            return True
        except PermanentTranscriptionError as exc:
            assert recording is not None  # None raises RecordingMissingError above
            logger.error("job %s: permanent provider failure: %s", job.id, exc)
            await svc.mark_failed(
                session,
                recording=recording,
                job_id=job.id,
                error=str(exc),
                model_used=model_used,
            )
            await _fail_job(session_factory, job_service, job, worker_id)
            return True
        except Exception:
            logger.exception("job %s: transient error; requeueing via job backoff", job.id)
            await _fail_job(session_factory, job_service, job, worker_id)
            return True


async def _complete_job(session_factory, job_service, job, worker_id) -> None:
    async with session_factory() as session:
        await job_service.complete(session, job, worker_id)
        await session.commit()


async def _fail_job(session_factory, job_service, job, worker_id) -> None:
    async with session_factory() as session:
        await job_service.fail(session, job, worker_id)
        await session.commit()


async def worker_loop(
    session_factory: Callable[[], AbstractAsyncContextManager[AsyncSession]],
    job_service,
    provider: SpeechToTextProvider,
    storage: StorageProvider,
    *,
    worker_id: str = "transcription-worker-1",
    poll_seconds: float = 2.0,
) -> None:
    while True:
        processed = await run_once(
            session_factory, job_service, provider, storage, worker_id=worker_id
        )
        if not processed:
            await asyncio.sleep(poll_seconds)


def main() -> None:  # pragma: no cover - wiring entrypoint
    from app.core.database import async_session_factory
    from app.modules.jobs.service import JobService

    asyncio.run(
        worker_loop(
            async_session_factory, JobService(), FasterWhisperProvider(), LocalStorageProvider()
        )
    )


if __name__ == "__main__":  # pragma: no cover
    main()
