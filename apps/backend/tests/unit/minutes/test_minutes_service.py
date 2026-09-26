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
    """Captura add/flush/execute; aserciones sobre estado, no interacciones."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.flushes = 0

    def add(self, o: object) -> None:
        self.added.append(o)

    async def execute(self, _stmt: object) -> _ScalarResult:
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
