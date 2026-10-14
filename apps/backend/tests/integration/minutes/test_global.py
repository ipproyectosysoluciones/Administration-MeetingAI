"""Minutes: listado global + delete por tenant — issue #119."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.minutes.conftest import api, register_admin, seed_meeting


async def _create_draft(app: FastAPI, meeting_id: uuid.UUID, token: str) -> dict:
    resp = await api(
        app,
        "POST",
        f"/api/v1/meetings/{meeting_id}/minutes",
        json={"title": "Acta", "content": "c"},
        token=token,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_list_global_minutes(app: FastAPI, session_factory: async_sessionmaker) -> None:
    add = await register_admin(app)
    token = add["access_token"]
    tenant_id = add["user"]["tenant_id"]
    meeting_1 = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    meeting_2 = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    drafts = [await _create_draft(app, m, token) for m in (meeting_1, meeting_2)]

    got = await api(app, "GET", "/api/v1/minutes?page=1&page_size=50", token=token)
    assert got.status_code == 200, got.text
    ids = {i["id"] for i in got.json()["items"]}
    assert {d["id"] for d in drafts} <= ids
    # con filtro de status
    got2 = await api(app, "GET", "/api/v1/minutes?status=draft&page=1", token=token)
    assert got2.status_code == 200, got2.text


async def test_list_global_minutes_filters(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    add = await register_admin(app)
    token = add["access_token"]
    tenant_id = add["user"]["tenant_id"]
    meeting = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    draft = await _create_draft(app, meeting, token)
    got = await api(app, "GET", "/api/v1/minutes?q=no_match_zzz&page=1&page_size=10", token=token)
    assert got.status_code == 200, got.text
    items = got.json()["items"]
    assert all(x["id"] != draft["id"] for x in items)


async def test_delete_minute(app: FastAPI, session_factory: async_sessionmaker) -> None:
    add = await register_admin(app)
    token = add["access_token"]
    tenant_id = add["user"]["tenant_id"]
    meeting = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    d = await _create_draft(app, meeting, token)
    dep = await api(app, "DELETE", f"/api/v1/minutes/{d['id']}", token=token)
    assert dep.status_code == 204, dep.text


async def test_delete_minute_cross_tenant(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    other = await register_admin(app)
    token = other["access_token"]
    tenant_id = other["user"]["tenant_id"]
    meeting = await seed_meeting(session_factory, uuid.UUID(tenant_id))
    draft = await _create_draft(app, meeting, token)
    wrong = await register_admin(app)
    token2 = wrong["access_token"]
    resp = await api(app, "DELETE", f"/api/v1/minutes/{draft['id']}", token=token2)
    assert resp.status_code == 404
