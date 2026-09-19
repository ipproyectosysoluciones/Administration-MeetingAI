"""Superset integration tests for meetings list UI (TASK-230)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from tests.integration.meetings.conftest import api, register_admin


async def _n_meetings(app: FastAPI, token: str, n: int) -> list[str]:
    ids: list[str] = []
    for i in range(n):
        start = datetime.now(UTC) + timedelta(days=10 + i)
        resp = await api(
            app,
            "POST",
            "/api/v1/meetings",
            json={
                "title": f"Junta #{i}",
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(hours=1)).isoformat(),
            },
            token=token,
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    return ids


async def test_list_pagination_and_filter(app: FastAPI) -> None:
    a = await register_admin(app)
    await _n_meetings(app, a["access_token"], 5)

    page1 = await api(app, "GET", "/api/v1/meetings?page=1&page_size=2", token=a["access_token"])
    assert page1.json()["total"] == 5
    assert page1.json()["pages"] == 3

    filtered = await api(
        app, "GET", "/api/v1/meetings?status=scheduled&page_size=10", token=a["access_token"]
    )
    assert filtered.json()["total"] == 5
    assert all(i["status"] == "scheduled" for i in filtered.json()["items"])


async def test_list_search_by_title(app: FastAPI) -> None:
    a = await register_admin(app)
    await _n_meetings(app, a["access_token"], 2)
    marker = f"unique-{uuid.uuid4().hex[:6]}"
    start = datetime.now(UTC) + timedelta(days=3)
    await api(
        app,
        "POST",
        "/api/v1/meetings",
        json={
            "title": f"Junta {marker}",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=1)).isoformat(),
        },
        token=a["access_token"],
    )

    resp = await api(app, "GET", f"/api/v1/meetings?q={marker}", token=a["access_token"])
    assert resp.json()["total"] == 1
    assert marker in resp.json()["items"][0]["title"]


async def test_list_requires_authentication(app: FastAPI) -> None:
    resp = await api(app, "GET", "/api/v1/meetings", token=None)
    assert resp.status_code == 401, resp.text
