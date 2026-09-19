"""TASK-240: cross-tenant isolation extended to meetings + participants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI

from tests.integration.isolation.conftest import TwoTenants, api

PATH = "/api/v1/meetings"


async def _create_meeting(app: FastAPI, token: str) -> str:
    start = datetime.now(UTC) + timedelta(days=2)
    resp = await api(
        app,
        "POST",
        PATH,
        json={
            "title": "Junta B",
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=1)).isoformat(),
        },
        token=token,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def test_meeting_get_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    meeting_b = await _create_meeting(app, two_tenants.b.token)
    resp = await api(app, "GET", f"{PATH}/{meeting_b}", token=two_tenants.a.token)
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "MEETING_NOT_FOUND"


async def test_meeting_patch_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    meeting_b = await _create_meeting(app, two_tenants.b.token)
    resp = await api(
        app, "PATCH", f"{PATH}/{meeting_b}", json={"title": "hackeada"}, token=two_tenants.a.token
    )
    assert resp.status_code == 404, resp.text


async def test_meeting_cancel_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    meeting_b = await _create_meeting(app, two_tenants.b.token)
    resp = await api(app, "POST", f"{PATH}/{meeting_b}/cancel", token=two_tenants.a.token)
    assert resp.status_code == 404, resp.text


async def test_meeting_list_scoped_to_own_tenant(app: FastAPI, two_tenants: TwoTenants) -> None:
    await _create_meeting(app, two_tenants.b.token)
    listing_a = await api(app, "GET", PATH, token=two_tenants.a.token)
    listing_b = await api(app, "GET", PATH, token=two_tenants.b.token)
    assert listing_b.json()["total"] >= 1
    assert all(
        item["organization_id"] == two_tenants.a.org_id for item in listing_a.json()["items"]
    )


async def test_participant_add_cross_tenant_meeting_is_404(
    app: FastAPI, two_tenants: TwoTenants
) -> None:
    meeting_b = await _create_meeting(app, two_tenants.b.token)
    resp = await api(
        app,
        "POST",
        f"{PATH}/{meeting_b}/participants",
        json={"external_email": "colado@ejemplo.com"},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_participant_remove_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants
) -> None:
    meeting_b = await _create_meeting(app, two_tenants.b.token)
    add = await api(
        app,
        "POST",
        f"{PATH}/{meeting_b}/participants",
        json={"external_email": "b-participant@ejemplo.com"},
        token=two_tenants.b.token,
    )
    assert add.status_code == 201
    pid = add.json()["id"]
    _ = await api(
        app, "DELETE", f"{PATH}/{meeting_b}/participants/{pid}", token=two_tenants.a.token
    )  # 404 expected
    # Both the meeting itself and the participant reference are invisible.
    still = await api(app, "GET", f"{PATH}/{meeting_b}/participants", token=two_tenants.b.token)
    assert any(p["id"] == pid for p in still.json()["items"])
