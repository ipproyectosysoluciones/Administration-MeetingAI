"""Integration: transcription read-only REST surface (TASK-304).

Covers permission gate, pagination, and the 404 cross-tenant contract
(existence never leaks: 404, never 403-forbidden-then-known).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.meetings.models import Meeting
from app.modules.organizations.models import Membership
from app.modules.recordings.models import Recording
from app.modules.transcription.provider import Segment, TranscriptionResult
from app.modules.transcription.service import TranscriptionService
from app.modules.users.models import User
from tests.integration.meetings.conftest import api, register_admin


async def _setup_draft(app: FastAPI, factory: async_sessionmaker) -> tuple[str, str, str]:
    """Register org admin, create a meeting, insert recording + draft transcript."""
    a = await register_admin(app)
    token = a["access_token"]

    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.email == a["user"]["email"]))
        ).scalar_one()
        membership = (
            await session.execute(select(Membership).where(Membership.user_id == user.id))
        ).scalar_one()
        meeting = Meeting(
            organization_id=membership.organization_id,
            title="Junta transcripción",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        session.add(meeting)
        await session.flush()
        recording_id = uuid.uuid4()
        rec = Recording(
            id=recording_id,
            meeting_id=meeting.id,
            tenant_id=meeting.organization_id,
            filename="a.mp3",
            content_type="audio/mpeg",
            size_bytes=1,
            sha256="0" * 64,
            storage_path=f"{meeting.organization_id}/{meeting.id}/{recording_id}",
            status="stored",
            uploaded_by=user.id,
        )
        session.add(rec)
        await session.flush()
        t = await TranscriptionService().create_draft(
            session,
            recording=rec,
            result=TranscriptionResult(
                text="hola",
                segments=[Segment(0.0, 1.0, "hola")],
                avg_confidence=0.9,
                language="es",
            ),
            job_id=None,
            model_used="small",
        )
        await session.commit()
    return token, str(recording_id), str(t.id)


async def test_get_transcription_ok(app, session_factory) -> None:
    token, _rid, tid = await _setup_draft(app, session_factory)
    resp = await api(app, "GET", f"/api/v1/transcriptions/{tid}", token=token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == tid
    assert body["status"] == "draft"


async def test_get_transcription_requires_auth(app, session_factory) -> None:
    _token, _rid, tid = await _setup_draft(app, session_factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/transcriptions/{tid}")
    assert resp.status_code in (401, 403)


async def test_get_transcription_cross_tenant_is_404(app, session_factory) -> None:
    _token, _rid, tid = await _setup_draft(app, session_factory)
    other = await register_admin(app, email=f"o-{uuid.uuid4().hex[:6]}@t.dev")
    resp = await api(app, "GET", f"/api/v1/transcriptions/{tid}", token=other["access_token"])
    # 404, never 403: existence must not leak across tenants.
    assert resp.status_code == 404


async def test_list_recordings_transcriptions(app, session_factory) -> None:
    token, rid, tid = await _setup_draft(app, session_factory)
    resp = await api(app, "GET", f"/api/v1/recordings/{rid}/transcriptions", token=token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert [i["id"] for i in body["items"]] == [tid]

    resp = await api(
        app, "GET", f"/api/v1/recordings/{rid}/transcriptions?page_size=51", token=token
    )
    assert resp.status_code == 422  # page_size > 50 is rejected by Query validation


async def test_list_unknown_recording_is_404(app, session_factory) -> None:
    token, _rid, _tid = await _setup_draft(app, session_factory)
    resp = await api(app, "GET", f"/api/v1/recordings/{uuid.uuid4()}/transcriptions", token=token)
    assert resp.status_code == 404
