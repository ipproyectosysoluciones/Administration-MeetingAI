"""MIN-102: MinutesService — transiciones append-only + audit."""

from __future__ import annotations

import pytest

from app.core.exceptions import APIError
from app.modules.minutes.models import Minute
from app.modules.minutes.service import MinutesService


class _ScalarResult:
    """Minimal fake for ``session.execute(...).scalar_one_or_none()``."""

    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class FakeSession:
    """Captura add/flush/execute; aserciones sobre estado, no interacciones.

    La primera llamada a ``execute`` responde el lookup de Meeting (truthy si
    existe, None si no); las siguientes responden el conteo de versiones (None).
    """

    def __init__(self, meeting_exists: bool = True) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0
        self._meeting_checked = False
        self._meeting_exists = meeting_exists

    def add(self, o: object) -> None:
        self.added.append(o)

    async def execute(self, _stmt: object) -> _ScalarResult:
        if not self._meeting_checked:
            self._meeting_checked = True
            return _ScalarResult(object() if self._meeting_exists else None)
        return _ScalarResult(None)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1


def _mk_minute(status: str = "draft") -> Minute:
    return Minute(status=status)


async def test_create_draft_sets_version_one_and_audits() -> None:
    svc = MinutesService()
    session = FakeSession()
    m = await svc.create_draft(
        session,
        meeting_id="meeting-1",  # type: ignore[arg-type]
        tenant_id="tenant-1",  # type: ignore[arg-type]
        title="Junta ordinaria",
        content="Resumen",
        created_by="user-1",  # type: ignore[arg-type]
    )
    assert m.status == "draft"
    assert m.version == 1
    assert m in session.added
    assert session.flushes >= 1


async def test_create_draft_404_on_missing_meeting() -> None:
    svc = MinutesService()
    session = FakeSession(meeting_exists=False)
    with pytest.raises(APIError) as exc:
        await svc.create_draft(
            session,
            meeting_id="meeting-x",  # type: ignore[arg-type]
            tenant_id="tenant-x",  # type: ignore[arg-type]
            title="T",
            content="C",
            created_by="u",  # type: ignore[arg-type]
        )
    assert exc.value.status_code == 404
    assert exc.value.code == "MEETING_NOT_FOUND"


async def test_publish_blocked_without_approval() -> None:
    svc = MinutesService()
    session = FakeSession()
    m = _mk_minute(status="draft")
    with pytest.raises(APIError):
        await svc.publish(session, minute=m, published_by="u", ip=None, user_agent=None)


async def test_archive_blocked_without_publish() -> None:
    svc = MinutesService()
    session = FakeSession()
    m = _mk_minute(status="approved")
    with pytest.raises(APIError):
        await svc.archive(session, minute=m, actor="u")


async def test_approve_blocked_without_review() -> None:
    svc = MinutesService()
    session = FakeSession()
    m = _mk_minute(status="draft")
    with pytest.raises(APIError):
        await svc.approve(session, minute=m, approved_by="u", ip=None, user_agent=None)
