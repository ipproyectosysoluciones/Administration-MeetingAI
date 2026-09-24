"""TASK-302: TranscriptionService — draft persistence semantics (unit, fakes only)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.transcription.provider import Segment, TranscriptionResult


def _fake_recording():
    class R:
        id = uuid.uuid4()
        meeting_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        storage_path = "t/m/r"

    return R()


def _result() -> TranscriptionResult:
    return TranscriptionResult(
        text="Hola mundo",
        segments=[Segment(start=0.0, end=1.5, text="Hola", speaker=None)],
        avg_confidence=0.9,
        language="es",
    )


class _CapturingSession:
    """Minimal session fake capturing adds (unit-level, no DB)."""

    def __init__(self) -> None:
        self.added: list = []
        self.committed = 0
        self.flushed = 0

    def add(self, row) -> None:
        self.added.append(row)

    async def flush(self) -> None:
        self.flushed += 1

    async def commit(self) -> None:
        self.committed += 1


async def test_create_draft_maps_all_fields() -> None:
    from app.modules.transcription.service import TranscriptionService

    svc = TranscriptionService()
    session = _CapturingSession()
    recording = _fake_recording()
    job_id = uuid.uuid4()

    t = await svc.create_draft(
        cast(AsyncSession, session),
        recording=recording,
        result=_result(),
        job_id=job_id,
        model_used="small",
    )

    assert t in session.added
    assert session.flushed == 1
    assert session.committed == 1
    assert t.recording_id == recording.id
    assert t.meeting_id == recording.meeting_id
    assert t.tenant_id == recording.tenant_id
    assert t.status == "draft"
    assert t.version == 1
    assert t.text == "Hola mundo"
    assert t.language == "es"
    assert t.avg_confidence == Decimal("0.9")
    assert t.model_used == "small"
    assert t.created_by_job_id == job_id
    assert t.segments == [{"start": 0.0, "end": 1.5, "text": "Hola", "speaker": None}]
    assert t.error is None


async def test_create_draft_language_defaults_to_es() -> None:
    from app.modules.transcription.service import TranscriptionService

    svc = TranscriptionService()
    session = _CapturingSession()
    result = TranscriptionResult(text="", segments=[], avg_confidence=None, language=None)

    t = await svc.create_draft(
        cast(AsyncSession, session),
        recording=_fake_recording(),
        result=result,
        job_id=None,
        model_used="small",
    )
    assert t.language == "es"


async def test_mark_failed_persists_failed_transcript() -> None:
    from app.modules.transcription.service import TranscriptionService

    svc = TranscriptionService()
    session = _CapturingSession()
    recording = _fake_recording()
    job_id = uuid.uuid4()

    t = await svc.mark_failed(
        cast(AsyncSession, session),
        recording=recording,
        job_id=job_id,
        error="corrupt audio",
        model_used="small",
    )

    assert t.status == "failed"
    assert t.error == "corrupt audio"
    assert t.text == ""
    assert t.segments == []
    assert session.committed == 1
