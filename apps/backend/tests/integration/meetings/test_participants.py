"""TASK-220/221: meeting participants integration tests (meetings-crud).

Follows the patterns of tests/integration/meetings/test_meetings.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.meetings.conftest import api, create_member, register_admin


async def _create_meeting(app: FastAPI, token: str) -> str:
    start = datetime.now(UTC) + timedelta(days=2)
    resp = await api(
        app,
        "POST",
        "/api/v1/meetings",
        json={
            "title": "Junta",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=1)).isoformat(),
        },
        token=token,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def test_add_internal_participant(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    user_id, _ = await create_member(
        session_factory, uuid.UUID(a["user"]["tenant_id"]), role="resident"
    )

    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"user_id": str(user_id), "role": "presenter"},
        token=a["access_token"],
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["user_id"] == str(user_id)


async def test_duplicate_participant_is_409(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    user_id, _ = await create_member(
        session_factory, uuid.UUID(a["user"]["tenant_id"]), role="resident"
    )

    for _ in range(2):
        await api(
            app,
            "POST",
            f"/api/v1/meetings/{meeting_id}/participants",
            json={"user_id": str(user_id)},
            token=a["access_token"],
        )

    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"user_id": str(user_id)},
        token=a["access_token"],
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "DUPLICATE_PARTICIPANT"


async def test_external_participant_by_email(app: FastAPI) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])

    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"external_email": "vecino@ejemplo.com", "role": "attendee"},
        token=a["access_token"],
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["external_email"] == "vecino@ejemplo.com"
    assert resp.json()["user_id"] is None


async def test_add_uses_only_one_channel(app: FastAPI) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"user_id": str(uuid.uuid4()), "external_email": "x@y.z"},
        token=a["access_token"],
    )
    assert resp.status_code == 422


async def test_internal_participant_from_other_tenant_404(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    b = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    other_user, _ = await create_member(
        session_factory, uuid.UUID(b["user"]["tenant_id"]), role="resident"
    )

    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"user_id": str(other_user)},
        token=a["access_token"],
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "PARTICIPANT_USER_NOT_FOUND"


async def test_remove_participant_and_audit(app: FastAPI) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    created = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"external_email": "audit-check@ejemplo.com"},
        token=a["access_token"],
    )
    pid = created.json()["id"]

    resp = await api(
        app,
        "DELETE",
        f"/api/v1/meetings/{meeting_id}/participants/{pid}",
        token=a["access_token"],
    )
    assert resp.status_code == 204, resp.text

    listing = await api(
        app,
        "GET",
        "/api/v1/audit?action=meeting.participant.remove&resource=meeting_participant",
        token=a["access_token"],
    )
    assert listing.json()["total"] >= 1


async def test_non_admin_cannot_manage_participants(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    meeting_id = await _create_meeting(app, a["access_token"])
    _, member_email = await create_member(
        session_factory, uuid.UUID(a["user"]["tenant_id"]), role="board_member"
    )
    login = await api(
        app,
        "POST",
        "/api/v1/auth/login",
        json={"email": member_email, "password": "memberPass123"},
    )
    member_token = login.json()["access_token"]

    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/participants",
        json={"external_email": "x@y.z"},
        token=member_token,
    )
    assert resp.status_code == 403, resp.text
