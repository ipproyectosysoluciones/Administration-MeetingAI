"""MIN-105: generate_draft_from_transcription (AI draft wiring)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.exceptions import APIError
from app.modules.minutes.service import MinutesService


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class FakeSession:
    """Devuelve Meeting (1º), Transcript (2º), Meeting (3º) y None (4º: versiones)."""

    def __init__(
        self,
        meeting: object | None = SimpleNamespace(title="Junta"),
        transcript: object | None = SimpleNamespace(text="Se acordó votar el presupuesto"),
    ) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0
        self._results = [meeting, transcript, meeting, None]
        self._idx = 0

    def add(self, o: object) -> None:
        self.added.append(o)

    async def execute(self, _stmt: object) -> _ScalarResult:
        value: object = None
        if self._idx < len(self._results):
            value = self._results[self._idx]
            self._idx += 1
        return _ScalarResult(value)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1


async def test_generates_draft_from_transcription() -> None:
    svc = MinutesService()
    session = FakeSession()
    m = await svc.generate_draft_from_transcription(
        session,
        meeting_id="meeting-1",  # type: ignore[arg-type]
        tenant_id="tenant-1",  # type: ignore[arg-type]
        created_by="user-1",  # type: ignore[arg-type]
    )
    assert m.status == "draft"
    assert "Resumen (Junta)" in m.content
    assert m.ai_provider == "mock"
    assert m in session.added


async def test_404_when_meeting_missing() -> None:
    svc = MinutesService()
    session = FakeSession(meeting=None)
    with pytest.raises(APIError) as exc:
        await svc.generate_draft_from_transcription(
            session,
            meeting_id="x",  # type: ignore[arg-type]
            tenant_id="t",  # type: ignore[arg-type]
            created_by="u",  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "MEETING_NOT_FOUND"


async def test_409_when_no_transcription() -> None:
    svc = MinutesService()
    session = FakeSession(transcript=None)
    with pytest.raises(APIError) as exc:
        await svc.generate_draft_from_transcription(
            session,
            meeting_id="m",  # type: ignore[arg-type]
            tenant_id="t",  # type: ignore[arg-type]
            created_by="u",  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "NO_TRANSCRIPTION"


async def test_409_when_empty_transcription() -> None:
    svc = MinutesService()
    session = FakeSession(transcript=SimpleNamespace(text="   "))
    with pytest.raises(APIError) as exc:
        await svc.generate_draft_from_transcription(
            session,
            meeting_id="m",  # type: ignore[arg-type]
            tenant_id="t",  # type: ignore[arg-type]
            created_by="u",  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "EMPTY_TRANSCRIPTION"
