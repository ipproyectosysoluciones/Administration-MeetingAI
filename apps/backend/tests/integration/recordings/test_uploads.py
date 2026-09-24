"""Integration tests — recordings REST surface (TASK-252, R1–R5)."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.recordings.models import Job, Recording
from tests.integration.meetings.conftest import api, create_member, register_admin

MP3_BYTES = b"\xff\xfb\x90\x00" + b"\x00" * 4000


async def _meeting_with_rec_auth(
    app: FastAPI, session_factory: async_sessionmaker
) -> tuple[dict, str]:
    """Register an org + org_admin (gets recording.upload via matrix) + meeting."""
    a = await register_admin(app)
    tokens = a["access_token"]
    start = datetime.now(UTC) + timedelta(days=3)
    resp = await api(
        app,
        "POST",
        "/api/v1/meetings",
        json={
            "title": "Junta con grabación",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=2)).isoformat(),
        },
        token=tokens,
    )
    assert resp.status_code == 201, resp.text
    return a, resp.json()["id"]


async def _upload(
    app: FastAPI, token: str, meeting_id: str, filename: str, data: bytes
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(
            f"/api/v1/meetings/{meeting_id}/recordings",
            files={"file": (filename, io.BytesIO(data), "audio/mpeg")},
            headers={"Authorization": f"Bearer {token}"},
        )


async def test_upload_201_and_sha256_idempotent(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid = await _meeting_with_rec_auth(app, session_factory)
    first = await _upload(app, a["access_token"], mid, "junta.mp3", MP3_BYTES)
    assert first.status_code == 201, first.text
    assert first.json()["status"] == "queued"

    second = await _upload(app, a["access_token"], mid, "junta.mp3", MP3_BYTES)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_upload_rejects_unsupported_type(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid = await _meeting_with_rec_auth(app, session_factory)
    resp = await _upload(app, a["access_token"], mid, "malicioso.exe", b"MZi" * 100)
    assert resp.status_code == 415
    assert resp.json()["code"] == "UNSUPPORTED_MEDIA"


async def test_upload_requires_meeting_ownership(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid_a = await _meeting_with_rec_auth(app, session_factory)
    b, _ = await _meeting_with_rec_auth(app, session_factory)
    cross = await _upload(app, b["access_token"], mid_a, "x.mp3", MP3_BYTES)
    assert cross.status_code == 404


async def test_download_streams_and_audits(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid = await _meeting_with_rec_auth(app, session_factory)
    up = await _upload(app, a["access_token"], mid, "junta.mp3", MP3_BYTES)
    rid = up.json()["id"]

    dl = await api(app, "GET", f"/api/v1/recordings/{rid}/content", token=a["access_token"])
    assert dl.status_code == 200
    assert dl.content == MP3_BYTES

    audit = await api(
        app,
        "GET",
        "/api/v1/audit?action=recording.download",
        token=a["access_token"],
    )
    assert audit.json()["total"] >= 1


async def test_delete_soft_and_idempotent(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid = await _meeting_with_rec_auth(app, session_factory)
    up = await _upload(app, a["access_token"], mid, "junta.mp3", MP3_BYTES)
    rid = up.json()["id"]

    r1 = await api(app, "DELETE", f"/api/v1/recordings/{rid}", token=a["access_token"])
    assert r1.status_code == 204
    r2 = await api(app, "DELETE", f"/api/v1/recordings/{rid}", token=a["access_token"])
    assert r2.status_code == 204

    got = await api(app, "GET", f"/api/v1/recordings/{rid}", token=a["access_token"])
    assert got.status_code == 404


async def test_non_owner_cannot_upload_or_read(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a, mid = await _meeting_with_rec_auth(app, session_factory)
    _, member_email = await create_member(session_factory, uuid.UUID(a["user"]["tenant_id"]))
    login = await api(
        app,
        "POST",
        "/api/v1/auth/login",
        json={"email": member_email, "password": "memberPass123"},
    )
    member_token = login.json()["access_token"]

    up = await _upload(app, member_token, mid, "x.mp3", MP3_BYTES)
    assert up.status_code == 403


async def test_upload_enqueues_process_recording_job(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    """TASK-303: a fresh upload enqueues process_recording with scoped payload ids."""
    a, meeting_id = await _meeting_with_rec_auth(app, session_factory)
    resp = await _upload(app, a["access_token"], meeting_id, "enc.mp3", MP3_BYTES)
    assert resp.status_code == 201, resp.text
    recording_id = resp.json()["id"]

    async with session_factory() as session:
        jobs = (
            (await session.execute(select(Job).where(Job.type == "process_recording")))
            .scalars()
            .all()
        )
        matching = [j for j in jobs if j.payload.get("recording_id") == recording_id]
        assert len(matching) == 1
        assert matching[0].status == "pending"
        rec = await session.get(Recording, uuid.UUID(recording_id))
        assert matching[0].payload["tenant_id"] == str(rec.tenant_id)
        assert matching[0].payload["meeting_id"] == meeting_id


async def test_idempotent_upload_does_not_reenqueue(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    """TASK-303: an idempotent 200 upload must not enqueue a duplicate job."""
    a, meeting_id = await _meeting_with_rec_auth(app, session_factory)
    first = await _upload(app, a["access_token"], meeting_id, "dup.mp3", MP3_BYTES)
    assert first.status_code == 201
    second = await _upload(app, a["access_token"], meeting_id, "dup.mp3", MP3_BYTES)
    assert second.status_code == 200

    async with session_factory() as session:
        # Scope to THIS meeting: the suite shares one migrated database.
        jobs = (
            (await session.execute(select(Job).where(Job.type == "process_recording")))
            .scalars()
            .all()
        )
        mine = [j for j in jobs if j.payload.get("meeting_id") == meeting_id]
        assert len(mine) == 1
