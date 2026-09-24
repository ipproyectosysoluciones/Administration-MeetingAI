"""TASK-302: worker run_once loop — claim, skip-if-draft, transient/permanent errors."""

from __future__ import annotations

import uuid
from typing import cast

from app.modules.recordings.providers import StorageProvider
from app.modules.transcription.provider import (
    PermanentTranscriptionError,
    Segment,
    SpeechToTextProvider,
    TranscriptionResult,
)
from app.modules.transcription.service import TranscriptionService


class _Job:
    def __init__(self, payload):
        self.id = uuid.uuid4()
        self.type = "process_recording"
        self.payload = payload


class FakeJobService:
    """In-memory stand-in for JobService (jobs.service is not exercised here)."""

    def __init__(self, job=None):
        self._job = job
        self.completed: list = []
        self.failed: list = []

    async def claim_next(self, session, worker_id):
        return self._job

    async def complete(self, session, job, worker_id):
        self.completed.append(job)

    async def fail(self, session, job, worker_id):
        self.failed.append(job)


class FakeProvider(SpeechToTextProvider):
    model_name = "fake-model"

    def __init__(self, result=None, exc=None):
        self.result = result or TranscriptionResult(
            text="ok", segments=[Segment(0.0, 1.0, "ok")], avg_confidence=0.9, language="es"
        )
        self.exc = exc
        self.calls = 0

    async def transcribe(self, audio_path, language=None):
        self.calls += 1
        if self.exc:
            raise self.exc
        return self.result


class FakeStorage(StorageProvider):
    def __init__(self, tmp_path):
        self._file = tmp_path / "a.wav"
        self._file.write_bytes(b"RIFF")

    async def store(self, key, stream):  # pragma: no cover - unused in worker tests
        raise NotImplementedError

    async def open_read(self, key):
        return open(self._file, "rb")

    async def exists(self, key):  # pragma: no cover
        return self._file.exists()


class FakeSessionFactory:
    def __init__(self, recording=None):
        self.recording = recording
        self.sessions: list = []

    def __call__(self):
        s = _FakeSession(self)
        self.sessions.append(s)
        return s


class _FakeSession:
    def __init__(self, factory):
        self.factory = factory

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        return None

    async def get(self, model, pk):
        return self.factory.recording


def _recording():
    class R:
        id = uuid.uuid4()
        meeting_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        storage_path = "k"

    return R()


async def test_run_once_processes_job_and_completes(tmp_path) -> None:
    from app.modules.transcription import worker

    recording = _recording()
    job = _Job({"recording_id": str(recording.id)})
    jobs = FakeJobService(job)
    provider = FakeProvider()
    created: list = []

    class Svc:
        async def get_active_draft(self, session, recording_id):
            return None

        async def create_draft(self, session, *, recording, result, job_id, model_used):
            created.append((recording.id, job_id))
            return object()

        async def mark_failed(self, session, *, recording, job_id, error, model_used):
            raise AssertionError("must not fail")

    factory = FakeSessionFactory(recording=recording)
    processed = await worker.run_once(
        factory,
        jobs,
        provider,
        FakeStorage(tmp_path),
        worker_id="w1",
        service=cast(TranscriptionService, Svc()),
    )

    assert processed is True
    assert jobs.completed == [job]
    assert jobs.failed == []
    assert provider.calls == 1
    assert created == [(recording.id, job.id)]


async def test_run_once_skips_existing_draft_without_calling_provider(tmp_path) -> None:
    from app.modules.transcription import worker

    recording = _recording()
    job = _Job({"recording_id": str(recording.id)})
    jobs = FakeJobService(job)
    provider = FakeProvider()

    class Svc:
        async def get_active_draft(self, session, recording_id):
            return object()

        async def create_draft(self, session, *, recording, result, job_id, model_used):
            raise AssertionError("must not create")

        async def mark_failed(self, session, *, recording, job_id, error, model_used):
            raise AssertionError("must not fail")

    factory = FakeSessionFactory(recording=recording)
    await worker.run_once(
        factory,
        jobs,
        provider,
        FakeStorage(tmp_path),
        worker_id="w1",
        service=cast(TranscriptionService, Svc()),
    )

    assert jobs.completed == [job]
    assert provider.calls == 0


async def test_run_once_transient_error_marks_job_failed(tmp_path) -> None:
    from app.modules.transcription import worker

    recording = _recording()
    job = _Job({"recording_id": str(recording.id)})
    jobs = FakeJobService(job)
    provider = FakeProvider(exc=TimeoutError("whisper busy"))

    class Svc:
        async def get_active_draft(self, session, recording_id):
            return None

        async def create_draft(self, session, *, recording, result, job_id, model_used):
            raise AssertionError("must not create")

        async def mark_failed(self, session, *, recording, job_id, error, model_used):
            raise AssertionError("transient errors must not mark transcript failed")

    factory = FakeSessionFactory(recording=recording)
    await worker.run_once(
        factory,
        jobs,
        provider,
        FakeStorage(tmp_path),
        worker_id="w1",
        service=cast(TranscriptionService, Svc()),
    )

    assert jobs.failed == [job]
    assert jobs.completed == []


async def test_run_once_missing_recording_fails_job_without_transcript(tmp_path) -> None:
    """No recording row -> FK would block a failed Transcript; only the job fails."""
    from app.modules.transcription import worker

    recording = _recording()
    job = _Job({"recording_id": str(recording.id)})
    jobs = FakeJobService(job)
    provider = FakeProvider()

    class Svc:
        async def get_active_draft(self, session, recording_id):
            return None

        async def create_draft(self, session, *, recording, result, job_id, model_used):
            raise AssertionError

        async def mark_failed(self, session, *, recording, job_id, error, model_used):
            raise AssertionError("cannot persist a failed transcript without a recording row")

    factory = FakeSessionFactory(recording=None)
    await worker.run_once(
        factory,
        jobs,
        provider,
        FakeStorage(tmp_path),
        worker_id="w1",
        service=cast(TranscriptionService, Svc()),
    )

    assert jobs.failed == [job]
    assert jobs.completed == []
    assert provider.calls == 0


async def test_run_once_corrupt_audio_marks_transcript_failed(tmp_path) -> None:
    from app.modules.transcription import worker

    recording = _recording()
    job = _Job({"recording_id": str(recording.id)})
    jobs = FakeJobService(job)
    provider = FakeProvider(exc=PermanentTranscriptionError("corrupt audio"))
    failed_rows: list = []

    class Svc:
        async def get_active_draft(self, session, recording_id):
            return None

        async def create_draft(self, session, *, recording, result, job_id, model_used):
            raise AssertionError

        async def mark_failed(self, session, *, recording, job_id, error, model_used):
            failed_rows.append(error)
            return object()

    factory = FakeSessionFactory(recording=recording)
    await worker.run_once(
        factory,
        jobs,
        provider,
        FakeStorage(tmp_path),
        worker_id="w1",
        service=cast(TranscriptionService, Svc()),
    )

    assert jobs.failed == [job]
    assert len(failed_rows) == 1
    assert "corrupt" in failed_rows[0].lower()


async def test_run_once_no_job_returns_false(tmp_path) -> None:
    from app.modules.transcription import worker

    factory = FakeSessionFactory()
    processed = await worker.run_once(
        factory,
        FakeJobService(None),
        FakeProvider(),
        FakeStorage(tmp_path),
        worker_id="w1",
        service=None,
    )
    assert processed is False
