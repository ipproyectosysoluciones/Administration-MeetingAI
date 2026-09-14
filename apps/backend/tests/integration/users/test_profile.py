"""TASK-050: self-service profile (GET/PATCH /users/me).

Covers the current-user profile with resolved permissions, self profile update, and the
non-self-elevation rule (cannot change email/roles/tenant → 403 FIELD_NOT_ALLOWED).
"""

from __future__ import annotations

from fastapi import FastAPI

from .conftest import _request, register


async def test_get_me_returns_profile_permissions_and_membership(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(app, "GET", "/api/v1/users/me", token=token)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == reg["user"]["id"]
    assert body["email"] == reg["user"]["email"]
    assert body["tenant_id"] == reg["user"]["tenant_id"]
    assert body["tenant_name"]
    assert "user.read" in body["permissions"]
    assert body["active_membership"]["organization_id"] == reg["user"]["tenant_id"]
    assert body["active_membership"]["role"] == "org_admin"


async def test_update_me_changes_name(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(
        app, "PATCH", "/api/v1/users/me", json={"full_name": "Updated Name"}, token=token
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Updated Name"


async def test_update_me_rejects_restricted_field(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(
        app, "PATCH", "/api/v1/users/me", json={"role": "super_admin"}, token=token
    )

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FIELD_NOT_ALLOWED"


async def test_update_me_cannot_change_email(app: FastAPI) -> None:
    reg = await register(app)
    token = reg["access_token"]

    resp = await _request(
        app, "PATCH", "/api/v1/users/me", json={"email": "elevated@example.com"}, token=token
    )

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "FIELD_NOT_ALLOWED"


async def test_get_me_requires_auth(app: FastAPI) -> None:
    resp = await _request(app, "GET", "/api/v1/users/me")
    assert resp.status_code == 401
