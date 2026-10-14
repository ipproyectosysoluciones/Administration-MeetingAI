"""Recordings y transcriptions: listados globales por tenant — issue #119."""
from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.meetings.conftest import api, register_admin
from tests.integration.recordings.conftest import app  # noqa: F401


async def _seed_recording(session_factory, tenant_id, user_id):
    from datetime import UTC, datetime, timedelta

    from app.modules.meetings.models import Meeting
    from app.modules.recordings.models import Recording

    async with session_factory() as session:
        meeting = Meeting(
            organization_id=uuid.UUID(tenant_id),
            title="Junta",
            starts_at=datetime.now(UTC) + timedelta(days=1),
            ends_at=datetime.now(UTC) + timedelta(days=1, hours=1),
        )
        session.add(meeting)
        await session.flush()
        recording = Recording(
            meeting_id=meeting.id,
            tenant_id=uuid.UUID(tenant_id),
            filename=f"{uuid.uuid4()}.mp3",
            content_type="audio/mpeg",
            size_bytes=1234,
            sha256="0" * 64,
            storage_path=f"/tmp/{uuid.uuid4()}.mp3",
            uploaded_by=uuid.UUID(user_id),
        )
        session.add(recording)
        await session.commit()
        return recording.id, meeting.id


async def test_list_global_recordings(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    rid, _ = await _seed_recording(session_factory, tenant_id, admin["user"]["id"])

    resp = await api(app, "GET", "/api/v1/recordings?page=1&page_size=10", token=token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "items" in body and "total" in body
    ids = {i["id"] for i in body["items"]}
    assert str(rid) in ids


async def test_list_global_transcriptions(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    rid, mid = await _seed_recording(session_factory, tenant_id, admin["user"]["id"])

    # Seed a transcription for that recording
    from app.modules.transcription.models import Transcript
    async with session_factory() as session:
        tr = Transcript(
            tenant_id=uuid.UUID(tenant_id),
            recording_id=rid,
            meeting_id=mid,
            text="Contenido de prueba",
            status="final",
        )
        session.add(tr)
        await session.commit()

    resp = await api(app, "GET", "/api/v1/transcriptions?page=1&page_size=10", token=token)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1


async def test_list_global_recordings_filters(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    await _seed_recording(session_factory, tenant_id, admin["user"]["id"])
    resp = await api(app, "GET", "/api/v1/recordings?status=completed&page=1", token=token)
    assert resp.status_code == 200, resp.text