"""MIN-103: minutes REST lifecycle + cross-tenant 404."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.minutes.conftest import api, register_admin, seed_meeting


async def _draft(app: FastAPI, meeting_id: uuid.UUID, token: str) -> dict:
    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/minutes",
        json={"title": "Acta junta ordinaria", "content": "Se acordó votar el presupuesto."},
        token=token,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_and_get_draft(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)

    draft = await _draft(app, meeting_id, token)
    assert draft["status"] == "draft"
    assert draft["version"] == 1
    assert draft["meeting_id"] == str(meeting_id)

    got = await api(app, "GET", f"/api/v1/minutes/{draft['id']}", token=token)
    assert got.status_code == 200
    assert got.json()["id"] == draft["id"]


async def test_list_meeting_minutes(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)

    await _draft(app, meeting_id, token)

    listed = await api(app, "GET", f"/api/v1/meetings/{meeting_id}/minutes", token=token)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert len(listed.json()["items"]) == 1


async def test_full_lifecycle(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)

    draft = await _draft(app, meeting_id, token)
    mid = draft["id"]

    reviewed = await api(app, "POST", f"/api/v1/minutes/{mid}/review", token=token)
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "review"

    approved = await api(app, "POST", f"/api/v1/minutes/{mid}/approve", token=token)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    published = await api(app, "POST", f"/api/v1/minutes/{mid}/publish", token=token)
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    archived = await api(app, "POST", f"/api/v1/minutes/{mid}/archive", token=token)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


async def test_invalid_transition_409(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin = await register_admin(app)
    token = admin["access_token"]
    tenant_id = admin["user"]["tenant_id"]
    meeting_id = await seed_meeting(session_factory, tenant_id)

    draft = await _draft(app, meeting_id, token)
    mid = draft["id"]

    # draft → approve is invalid (must review first)
    resp = await api(app, "POST", f"/api/v1/minutes/{mid}/approve", token=token)
    assert resp.status_code == 409
    assert resp.json()["code"] == "MINUTE_INVALID_STATE"


async def test_cross_tenant_404(app: FastAPI, session_factory: async_sessionmaker) -> None:
    admin_a = await register_admin(app)
    admin_b = await register_admin(app)
    token_a = admin_a["access_token"]
    token_b = admin_b["access_token"]
    meeting_a = await seed_meeting(session_factory, admin_a["user"]["tenant_id"])

    draft_a = await _draft(app, meeting_a, token_a)

    # tenant B cannot see tenant A's minute → 404 (no existence leak)
    resp = await api(app, "GET", f"/api/v1/minutes/{draft_a['id']}", token=token_b)
    assert resp.status_code == 404
    assert resp.json()["code"] == "MINUTE_NOT_FOUND"
