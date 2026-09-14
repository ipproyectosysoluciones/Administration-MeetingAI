"""TASK-070: custom role CRUD per organization (spec.rbac §custom roles).

Custom roles are tenant-scoped, isolated across tenants (404, not 403/200), and
system/base roles are immutable.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI

from .conftest import _request, permission_id_by_name, register


async def _list_roles(app: FastAPI, token: str) -> list[dict[str, Any]]:
    resp = await _request(app, "GET", "/api/v1/rbac/roles", token=token)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]


async def test_create_custom_role(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    perm_id = await permission_id_by_name(app, token, "organization.read")
    resp = await _request(
        app,
        "POST",
        "/api/v1/rbac/roles",
        json={
            "name": "custom_manager",
            "display_name": "Custom Manager",
            "description": "Manager with limited perms",
            "permission_ids": [perm_id],
        },
        token=token,
    )
    assert resp.status_code == 201, resp.text
    role = resp.json()
    assert role["is_system"] is False
    assert role["organization_id"] == a["user"]["tenant_id"]
    assert [p["name"] for p in role["permissions"]] == ["organization.read"]


async def test_create_role_system_name_reserved(app: FastAPI) -> None:
    a = await register(app)
    resp = await _request(
        app,
        "POST",
        "/api/v1/rbac/roles",
        json={"name": "org_admin", "display_name": "Fake"},
        token=a["access_token"],
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "SYSTEM_ROLE_NAME_RESERVED"


async def test_create_role_duplicate_name_conflict(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    payload: dict[str, object] = {"name": "custom_dup", "display_name": "Dup"}
    first = await _request(app, "POST", "/api/v1/rbac/roles", json=payload, token=token)
    assert first.status_code == 201
    resp = await _request(app, "POST", "/api/v1/rbac/roles", json=payload, token=token)
    assert resp.status_code == 409
    assert resp.json()["code"] == "ROLE_NAME_EXISTS"


async def test_create_role_unknown_permission_404(app: FastAPI) -> None:
    a = await register(app)
    resp = await _request(
        app,
        "POST",
        "/api/v1/rbac/roles",
        json={"name": "custom_x", "display_name": "X", "permission_ids": [str(uuid.uuid4())]},
        token=a["access_token"],
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PERMISSION_NOT_FOUND"


async def test_update_custom_role(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    perm_id = await permission_id_by_name(app, token, "organization.read")
    created = (
        await _request(
            app,
            "POST",
            "/api/v1/rbac/roles",
            json={"name": "custom_upd", "display_name": "Old"},
            token=token,
        )
    ).json()
    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/rbac/roles/{created['id']}",
        json={"display_name": "New Name", "permission_ids": [perm_id]},
        token=token,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["display_name"] == "New Name"
    assert [p["id"] for p in body["permissions"]] == [perm_id]


async def test_update_base_role_immutable(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    base_roles = await _list_roles(app, token)
    base = next(r for r in base_roles if r["name"] == "secretary")
    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/rbac/roles/{base['id']}",
        json={"display_name": "Hacked"},
        token=token,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "SYSTEM_ROLE_IMMUTABLE"


async def test_delete_custom_role(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    created = (
        await _request(
            app,
            "POST",
            "/api/v1/rbac/roles",
            json={"name": "custom_del", "display_name": "Del"},
            token=token,
        )
    ).json()
    resp = await _request(app, "DELETE", f"/api/v1/rbac/roles/{created['id']}", token=token)
    assert resp.status_code == 200, resp.text
    names = {r["name"] for r in await _list_roles(app, token)}
    assert "custom_del" not in names


async def test_delete_base_role_forbidden(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    base_roles = await _list_roles(app, token)
    base = next(r for r in base_roles if r["name"] == "guest")
    resp = await _request(app, "DELETE", f"/api/v1/rbac/roles/{base['id']}", token=token)
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_CANNOT_DELETE"


async def test_cross_tenant_role_invisible(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    created = (
        await _request(
            app,
            "POST",
            "/api/v1/rbac/roles",
            json={"name": "custom_a", "display_name": "Tenant A role"},
            token=a["access_token"],
        )
    ).json()
    # B never sees A's role in listings
    names_b = {r["name"] for r in await _list_roles(app, b["access_token"])}
    assert "custom_a" not in names_b
    # Cross-tenant mutation attempts get 404 (not 403) to avoid existence leaks
    for method, path in (
        ("PATCH", f"/api/v1/rbac/roles/{created['id']}"),
        ("DELETE", f"/api/v1/rbac/roles/{created['id']}"),
    ):
        body: dict[str, object] | None = {"display_name": "x"} if method == "PATCH" else None
        resp = await _request(app, method, path, json=body, token=b["access_token"])
        assert resp.status_code == 404, (method, resp.text)
