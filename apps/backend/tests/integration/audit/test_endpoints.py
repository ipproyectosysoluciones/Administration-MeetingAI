"""TASK-080: GET /audit + GET /audit/{event_id} integration tests.

Contract: api-contract.md §6 — tenant-scoped, paginated, filtered, append-only
read endpoints guarded by the ``audit.read`` permission. Audit capture itself
(e.g. login writes an ``auth.login`` event) is exercised via the endpoint.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.audit.models import AuditEvent
from tests.integration.audit.conftest import api, create_member, register_admin


def make_event(
    *,
    actor_user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    action: str = "auth.login",
    resource: str = "auth",
    hours_ago: int = 0,
) -> AuditEvent:
    return AuditEvent(
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        action=action,
        resource=resource,
        timestamp=datetime.now(UTC) - timedelta(hours=hours_ago),
        metadata_json={},
    )


async def _login(app: FastAPI, email: str, password: str) -> dict[str, object]:
    """Login a non-admin user (no MFA gate) and return the token body."""
    resp = await api(app, "POST", "/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    body: dict[str, object] = resp.json()
    return body


async def _seed_events(session_factory: async_sessionmaker, events: list[AuditEvent]) -> None:
    async with session_factory() as session:
        session.add_all(events)
        await session.commit()


# --- GET /audit ---------------------------------------------------------------


async def test_audit_list_returns_only_current_tenant(app: FastAPI) -> None:
    a = await register_admin(app)
    b = await register_admin(app)
    tenant_a = a["user"]["tenant_id"]
    tenant_b = b["user"]["tenant_id"]
    assert tenant_a != tenant_b

    resp = await api(app, "GET", "/api/v1/audit", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert all(item["tenant_id"] == tenant_a for item in body["items"])


async def test_audit_list_pagination_is_consistent(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    actor = uuid.UUID(a["user"]["id"])
    events = [make_event(actor_user_id=actor, tenant_id=tenant_a, hours_ago=i) for i in range(7)]
    # Noise events that must never appear in the filtered listing.
    events.append(
        make_event(actor_user_id=actor, tenant_id=tenant_a, action="user.create", resource="user")
    )
    await _seed_events(session_factory, events)

    async def fetch(page: int) -> list[dict]:
        resp = await api(
            app,
            "GET",
            f"/api/v1/audit?page={page}&page_size=2&action=auth.login&resource=auth",
            token=a["access_token"],
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 7
        assert body["pages"] == 4
        assert body["page"] == page
        return body["items"]

    page1 = await fetch(1)
    page2 = await fetch(2)
    page4 = await fetch(4)
    assert len(page1) == 2 and len(page2) == 2 and len(page4) == 1
    ids = [item["id"] for item in page1 + page2 + page4]
    assert len(set(ids)) == 5


async def test_audit_list_filters_by_action(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    actor = uuid.UUID(a["user"]["id"])
    events = [
        make_event(actor_user_id=actor, tenant_id=tenant_a, action="auth.login"),
        make_event(actor_user_id=actor, tenant_id=tenant_a, action="auth.login"),
        make_event(actor_user_id=actor, tenant_id=tenant_a, action="user.create", resource="user"),
    ]
    await _seed_events(session_factory, events)

    resp = await api(app, "GET", "/api/v1/audit?action=auth.login", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert all(item["action"] == "auth.login" for item in body["items"])


async def test_audit_list_filters_by_date_range(app: FastAPI) -> None:
    a = await register_admin(app)
    resp_all = await api(app, "GET", "/api/v1/audit", token=a["access_token"])
    total = resp_all.json()["total"]
    assert total >= 1

    future = "2999-01-01T00:00:00Z"
    resp = await api(app, "GET", f"/api/v1/audit?date_from={future}", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 0

    past = "2000-01-01T00:00:00Z"
    resp2 = await api(app, "GET", f"/api/v1/audit?date_from={past}", token=a["access_token"])
    assert resp2.json()["total"] == total


async def test_audit_list_rejects_invalid_date(app: FastAPI) -> None:
    a = await register_admin(app)
    resp = await api(app, "GET", "/api/v1/audit?date_from=not-a-date", token=a["access_token"])
    assert resp.status_code == 400, resp.text


# --- GET /audit/{event_id} ----------------------------------------------------


async def test_audit_event_detail_same_tenant(app: FastAPI) -> None:
    a = await register_admin(app)
    listing = await api(app, "GET", "/api/v1/audit", token=a["access_token"])
    event_id = listing.json()["items"][0]["id"]

    resp = await api(app, "GET", f"/api/v1/audit/{event_id}", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == event_id


async def test_audit_event_detail_cross_tenant_is_404(app: FastAPI) -> None:
    a = await register_admin(app)
    b = await register_admin(app)
    listing_b = await api(app, "GET", "/api/v1/audit", token=b["access_token"])
    event_b = listing_b.json()["items"][0]["id"]

    resp = await api(app, "GET", f"/api/v1/audit/{event_b}", token=a["access_token"])
    assert resp.status_code == 404, resp.text
    body = resp.json()
    code = body.get("error", {}).get("code", body.get("code"))
    assert code == "AUDIT_EVENT_NOT_FOUND"


async def test_audit_event_detail_unknown_id_is_404(app: FastAPI) -> None:
    a = await register_admin(app)
    resp = await api(app, "GET", f"/api/v1/audit/{uuid.uuid4()}", token=a["access_token"])
    assert resp.status_code == 404, resp.text


# --- Authz / authn ------------------------------------------------------------


async def test_audit_requires_authentication(app: FastAPI) -> None:
    resp = await api(app, "GET", "/api/v1/audit")
    assert resp.status_code == 401, resp.text


async def test_audit_requires_audit_read_permission(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    """A resident without audit.read gets 403 on both endpoints."""
    a = await register_admin(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    _, member_email, member_password = await create_member(session_factory, tenant_a)
    body = await _login(app, member_email, member_password)
    resident_token = body["access_token"]

    resp_list = await api(app, "GET", "/api/v1/audit", token=resident_token)
    assert resp_list.status_code == 403, resp_list.text

    listing = await api(app, "GET", "/api/v1/audit", token=a["access_token"])
    event_id = listing.json()["items"][0]["id"]
    resp_detail = await api(app, "GET", f"/api/v1/audit/{event_id}", token=resident_token)
    assert resp_detail.status_code == 403, resp_detail.text


# --- Append-only --------------------------------------------------------------


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
async def test_audit_is_read_only(app: FastAPI, method: str) -> None:
    a = await register_admin(app)
    listing = await api(app, "GET", "/api/v1/audit", token=a["access_token"])
    event_id = listing.json()["items"][0]["id"]

    for path in ("/api/v1/audit", f"/api/v1/audit/{event_id}"):
        resp = await api(app, method, path, json={"action": "x"}, token=a["access_token"])
        assert resp.status_code in (404, 405), f"{method} {path}: {resp.status_code}"


# --- Capture wiring -----------------------------------------------------------


async def test_login_event_is_visible_via_audit_endpoint(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register_admin(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, member_email, member_password = await create_member(session_factory, tenant_a)
    await _login(app, member_email, member_password)

    resp = await api(app, "GET", "/api/v1/audit?action=auth.login", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["actor_user_id"] == str(member_id) for item in body["items"])
