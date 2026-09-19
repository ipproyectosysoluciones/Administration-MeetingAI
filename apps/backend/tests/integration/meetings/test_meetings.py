"""TASK-210/211: meetings CRUD integration tests (api-contract.md §meetings).

Patterns follow tests/integration/users + audit. Real FastAPI app + test PostgreSQL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from tests.integration.meetings.conftest import api, register_admin


def _meeting_payload(**overrides: object) -> dict[str, object]:
    start = datetime.now(UTC) + timedelta(days=2)
    payload: dict[str, object] = {
        "title": "Asamblea Ordinaria",
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=2)).isoformat(),
        "modality": "virtual",
    }
    payload.update(overrides)
    return payload


async def test_create_meeting_returns_201_and_audits(app: FastAPI) -> None:
    a = await register_admin(app)
    resp = await api(
        app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"]
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["title"] == "Asamblea Ordinaria"
    assert body["status"] == "scheduled"

    listing = await api(app, "GET", "/api/v1/audit?action=meeting.create", token=a["access_token"])
    assert listing.status_code == 200, listing.text
    assert listing.json()["total"] >= 1


async def test_create_rejects_end_before_start(app: FastAPI) -> None:
    a = await register_admin(app)
    start = datetime.now(UTC) + timedelta(days=2)
    resp = await api(
        app,
        "POST",
        "/api/v1/meetings",
        json=_meeting_payload(
            starts_at=start.isoformat(), ends_at=(start - timedelta(hours=1)).isoformat()
        ),
        token=a["access_token"],
    )
    assert resp.status_code == 422, resp.text


async def test_list_is_tenant_scoped(app: FastAPI) -> None:
    a = await register_admin(app)
    b = await register_admin(app)
    await api(app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"])

    response_b = await api(app, "GET", "/api/v1/meetings", token=b["access_token"])
    assert response_b.status_code == 200
    assert response_b.json()["total"] == 0

    response_a = await api(app, "GET", "/api/v1/meetings", token=a["access_token"])
    assert response_a.json()["total"] == 1


async def test_get_cross_tenant_is_404(app: FastAPI) -> None:
    a = await register_admin(app)
    b = await register_admin(app)
    created = await api(
        app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"]
    )
    meeting_id = created.json()["id"]

    resp = await api(app, "GET", f"/api/v1/meetings/{meeting_id}", token=b["access_token"])
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "MEETING_NOT_FOUND"


async def test_board_member_can_read_but_cannot_cancel(app: FastAPI, session_factory) -> None:
    """board_member has meeting.read but NOT meeting.cancel; cancel returns 403."""
    from tests.integration.meetings.conftest import create_member

    a = await register_admin(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    _, member_email = await create_member(session_factory, tenant_a, role="board_member")
    login = await api(
        app,
        "POST",
        "/api/v1/auth/login",
        json={"email": member_email, "password": "memberPass123"},
    )
    assert login.status_code == 200, login.text
    member_token = login.json()["access_token"]

    created = await api(
        app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"]
    )
    meeting_id = created.json()["id"]

    read_resp = await api(app, "GET", f"/api/v1/meetings/{meeting_id}", token=member_token)
    assert read_resp.status_code == 200, read_resp.text

    cancel = await api(app, "POST", f"/api/v1/meetings/{meeting_id}/cancel", token=member_token)
    assert cancel.status_code == 403, cancel.text


async def test_update_invalid_transition_is_422(app: FastAPI) -> None:
    a = await register_admin(app)
    created = await api(
        app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"]
    )
    meeting_id = created.json()["id"]
    resp = await api(
        app,
        "PATCH",
        f"/api/v1/meetings/{meeting_id}",
        json={"status": "finished"},
        token=a["access_token"],
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "INVALID_STATUS_TRANSITION"


async def test_status_flow(app: FastAPI) -> None:
    a = await register_admin(app)
    created = await api(
        app, "POST", "/api/v1/meetings", json=_meeting_payload(), token=a["access_token"]
    )
    meeting_id = created.json()["id"]
    for to in ("in_progress", "finished"):
        resp = await api(
            app,
            "PATCH",
            f"/api/v1/meetings/{meeting_id}",
            json={"status": to},
            token=a["access_token"],
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == to

    # finished is terminal
    resp = await api(
        app,
        "PATCH",
        f"/api/v1/meetings/{meeting_id}",
        json={"status": "cancelled"},
        token=a["access_token"],
    )
    assert resp.status_code == 422
