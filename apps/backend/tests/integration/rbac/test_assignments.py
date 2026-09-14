"""TASK-070: role↔permission and user↔role assignment (spec.rbac §assignments).

Resolution is recomputed after assignment via ``GET /users/me`` permissions, and
cross-tenant access is 404 (never 403) to avoid existence leaks.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings

from .conftest import _request, create_member, mint_token, permission_id_by_name, register


async def _create_custom_role(
    app: FastAPI, token: str, name: str, permission_ids: list[str] | None = None
) -> dict[str, Any]:
    body: dict[str, object] = {"name": name, "display_name": name.replace("_", " ").title()}
    if permission_ids is not None:
        body["permission_ids"] = permission_ids
    resp = await _request(app, "POST", "/api/v1/rbac/roles", json=body, token=token)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_assign_permission_to_custom_role(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    role = await _create_custom_role(app, token, "assign_perm")
    perm_id = await permission_id_by_name(app, token, "organization.read")
    resp2 = await _request(
        app,
        "POST",
        f"/api/v1/rbac/roles/{role['id']}/permissions",
        json={"permission_id": perm_id},
        token=token,
    )
    assert resp2.status_code == 200, resp2.text
    assert [p["id"] for p in resp2.json()["permissions"]] == [perm_id]


async def test_assign_permission_base_role_immutable(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    roles = (await _request(app, "GET", "/api/v1/rbac/roles", token=token)).json()["items"]
    guest = next(r for r in roles if r["name"] == "guest")
    perm_id = await permission_id_by_name(app, token, "user.delete")
    resp = await _request(
        app,
        "POST",
        f"/api/v1/rbac/roles/{guest['id']}/permissions",
        json={"permission_id": perm_id},
        token=token,
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "SYSTEM_ROLE_IMMUTABLE"


async def test_revoke_permission_from_role(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    perm_id = await permission_id_by_name(app, token, "organization.read")
    role = await _create_custom_role(app, token, "revoke_perm", [perm_id])
    resp = await _request(
        app,
        "DELETE",
        f"/api/v1/rbac/roles/{role['id']}/permissions/{perm_id}",
        token=token,
    )
    assert resp.status_code == 200, resp.text
    # Triangulate: revoking again is a 404 ROLE_PERMISSION_NOT_FOUND
    resp2 = await _request(
        app,
        "DELETE",
        f"/api/v1/rbac/roles/{role['id']}/permissions/{perm_id}",
        token=token,
    )
    assert resp2.status_code == 404
    assert resp2.json()["code"] == "ROLE_PERMISSION_NOT_FOUND"


async def test_assign_role_to_user_changes_resolution(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant, role="resident")
    perm_id = await permission_id_by_name(app, token, "organization.update")
    role = await _create_custom_role(app, token, "org_editor", [perm_id])

    resp = await _request(
        app,
        "POST",
        f"/api/v1/rbac/users/{member_id}/roles",
        json={"role_id": role["id"]},
        token=token,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["user_role"]["organization_id"] == str(tenant)

    # Union resolution: resident (organization.read) + org_editor (organization.update)
    member_token = await mint_token(settings, member_id)
    me = await _request(app, "GET", "/api/v1/users/me", token=member_token)
    perms = set(me.json()["permissions"])
    assert {"organization.read", "organization.update"} <= perms


async def test_assign_role_duplicate_conflict(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant, role="resident")
    role = await _create_custom_role(app, token, "dup_assign")
    path = f"/api/v1/rbac/users/{member_id}/roles"
    for expected in (200, 409):
        resp = await _request(app, "POST", path, json={"role_id": role["id"]}, token=token)
        assert resp.status_code == expected, resp.text
    assert resp.json()["code"] == "ROLE_ASSIGNMENT_EXISTS"


async def test_assign_unknown_user_or_role_404(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    role = await _create_custom_role(app, token, "four_oh_four")
    resp = await _request(
        app,
        "POST",
        f"/api/v1/rbac/users/{uuid.uuid4()}/roles",
        json={"role_id": role["id"]},
        token=token,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "USER_NOT_FOUND"
    # user exists (admin themself) but role id does not
    resp = await _request(
        app,
        "POST",
        f"/api/v1/rbac/users/{a['user']['id']}/roles",
        json={"role_id": str(uuid.uuid4())},
        token=token,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ROLE_NOT_FOUND"


async def test_revoke_role_from_user(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant, role="resident")
    role = await _create_custom_role(app, token, "revokable")
    await _request(
        app,
        "POST",
        f"/api/v1/rbac/users/{member_id}/roles",
        json={"role_id": role["id"]},
        token=token,
    )
    resp = await _request(
        app, "DELETE", f"/api/v1/rbac/users/{member_id}/roles/{role['id']}", token=token
    )
    assert resp.status_code == 200, resp.text
    # Triangulate: second revoke is a 404 USER_ROLE_NOT_FOUND
    resp2 = await _request(
        app, "DELETE", f"/api/v1/rbac/users/{member_id}/roles/{role['id']}", token=token
    )
    assert resp2.status_code == 404
    assert resp2.json()["code"] == "USER_ROLE_NOT_FOUND"


async def test_revoke_last_org_admin_protected(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    roles = (await _request(app, "GET", "/api/v1/rbac/roles", token=token)).json()["items"]
    org_admin = next(r for r in roles if r["name"] == "org_admin")
    user_id = a["user"]["id"]
    resp = await _request(
        app, "DELETE", f"/api/v1/rbac/users/{user_id}/roles/{org_admin['id']}", token=token
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "LAST_ADMIN_PROTECTED"


async def test_cross_tenant_assignment_404(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    role_a = await _create_custom_role(app, a["access_token"], "tenant_a_only")
    # B cannot see/assign A's custom role to B's admin
    resp = await _request(
        app,
        "POST",
        f"/api/v1/rbac/users/{b['user']['id']}/roles",
        json={"role_id": role_a["id"]},
        token=b["access_token"],
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "ROLE_NOT_FOUND"
    # B cannot revoke from A's admin (user not in B's tenant)
    resp_roles = await _request(app, "GET", "/api/v1/rbac/roles", token=a["access_token"])
    org_admin = next(r for r in resp_roles.json()["items"] if r["name"] == "org_admin")
    resp = await _request(
        app,
        "DELETE",
        f"/api/v1/rbac/users/{a['user']['id']}/roles/{org_admin['id']}",
        token=b["access_token"],
    )
    assert resp.status_code == 404
