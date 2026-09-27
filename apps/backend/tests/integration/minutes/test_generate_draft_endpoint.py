"""MIN-105: POST /meetings/{id}/minutes/generate (AI draft wiring)."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.recordings.models import Recording
from app.modules.transcription.models import Transcript
from tests.integration.minutes.conftest import api, register_admin, seed_meeting


async def _seed_transcript(
    session_factory: async_sessionmaker,
    meeting_id: uuid.UUID,
    tenant_id: uuid.UUID,
    uploaded_by: uuid.UUID,
) -> None:
    async with session_factory() as session:
        recording = Recording(
            meeting_id=meeting_id,
            tenant_id=tenant_id,
            filename="a.mp3",
            content_type="audio/mpeg",
            size_bytes=10,
            sha256="0" * 64,
            storage_path=f"{tenant_id}/{meeting_id}/rec",
            uploaded_by=uploaded_by,
        )
        session.add(recording)
        await session.flush()
        session.add(
            Transcript(
                recording_id=recording.id,
                meeting_id=meeting_id,
                tenant_id=tenant_id,
                text="Se acordó votar el presupuesto y aprobar el plan de obra.",
                status="final",
            )
        )
        await session.commit()


async def test_generate_draft_endpoint(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    user_id = admin["user"]["id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)
    await _seed_transcript(session_factory, meeting_id, tenant_id, user_id)

    resp = await api(app, "POST", f"/api/v1/meetings/{meeting_id}/minutes/generate", token=token)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "draft"
    assert "Resumen" in body["content"]
    assert body["ai_provider"] == "mock"


async def test_generate_409_no_transcription(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)

    resp = await api(app, "POST", f"/api/v1/meetings/{meeting_id}/minutes/generate", token=token)
    assert resp.status_code == 409
    assert resp.json()["code"] == "NO_TRANSCRIPTION"
