"""TASK-090 — cross-tenant isolation matrix.

Rule under test (api-contract.md conventions): a request authenticated as tenant A
that references a resource of tenant B MUST get **404** (never 403, never data).
Existence leaks via status codes, error bodies, or list responses are defects.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.audit.models import AuditEvent
from tests.integration.audit.conftest import api, create_member
from tests.integration.isolation.conftest import (
    Tenant,
    TwoTenants,
    create_property,
)

# --- resource seeding in tenant B --------------------------------------------


async def _seed_role(app: FastAPI, tenant: Tenant) -> str:
    resp = await api(
        app,
        "POST",
        "/api/v1/rbac/roles",
        json={
            "name": f"custom_{uuid.uuid4().hex[:8]}",
            "display_name": "Custom Role B",
        },
        token=tenant.token,
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


async def _seed_audit_event(session_factory: async_sessionmaker, tenant: Tenant) -> uuid.UUID:
    """Seed one audit event in tenant B (login event via real user login is async-heavy;
    direct insert mirrors the capture path used by TASK-080 tests)."""
    event = AuditEvent(
        actor_user_id=uuid.UUID(tenant.user_id),
        tenant_id=uuid.UUID(tenant.org_id),
        action="isolation.probe",
        resource="tenant",
        metadata_json={},
    )
    async with session_factory() as session:
        session.add(event)
        await session.commit()
        return event.id


# --- organizations --------------------------------------------------------------


async def test_org_delete_requires_super_admin(app: FastAPI, two_tenants: TwoTenants) -> None:
    """Org deletion is super-admin only; a cross-tenant caller gets 403 regardless of existence.

    This endpoint intentionally diverges from the 404 convention: it is protected by the
    is_super_admin flag, not by tenant scoping, so no existence information leaks.
    """
    resp = await api(
        app, "DELETE", f"/api/v1/organizations/{two_tenants.b.org_id}", token=two_tenants.a.token
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "SUPER_ADMIN_REQUIRED"


async def test_property_patch_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    prop_b = await create_property(app, two_tenants.b, "Propiedad de B")
    resp = await api(
        app,
        "PATCH",
        f"/api/v1/organizations/me/properties/{prop_b}",
        json={"name": "hackeado"},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_property_delete_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    prop_b = await create_property(app, two_tenants.b, "Propiedad de B")
    resp = await api(
        app, "DELETE", f"/api/v1/organizations/me/properties/{prop_b}", token=two_tenants.a.token
    )
    assert resp.status_code == 404, resp.text


async def test_property_list_only_own_tenant(app: FastAPI, two_tenants: TwoTenants) -> None:
    prop_b = await create_property(app, two_tenants.b, "Solo de B")
    resp = await api(app, "GET", "/api/v1/organizations/me/properties", token=two_tenants.a.token)
    assert resp.status_code == 200, resp.text
    ids = [p["id"] for p in resp.json()["items"]]
    assert prop_b not in ids


async def test_membership_patch_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants, session_factory: async_sessionmaker
) -> None:
    user_b, _, _ = await create_member(session_factory, uuid.UUID(two_tenants.b.org_id))
    memberships_b = await api(
        app, "GET", "/api/v1/organizations/me/memberships", token=two_tenants.b.token
    )
    assert memberships_b.status_code == 200, memberships_b.text
    items = memberships_b.json()["items"]
    target = next(m for m in items if m["user_id"] == str(user_b))

    resp = await api(
        app,
        "PATCH",
        f"/api/v1/organizations/me/memberships/{target['id']}",
        json={"role": "org_admin"},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_membership_delete_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants, session_factory: async_sessionmaker
) -> None:
    user_b, _, _ = await create_member(session_factory, uuid.UUID(two_tenants.b.org_id))
    memberships_b = await api(
        app, "GET", "/api/v1/organizations/me/memberships", token=two_tenants.b.token
    )
    target = next(m for m in memberships_b.json()["items"] if m["user_id"] == str(user_b))

    resp = await api(
        app,
        "DELETE",
        f"/api/v1/organizations/me/memberships/{target['id']}",
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


# --- users ----------------------------------------------------------------------


async def test_users_get_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    resp = await api(
        app, "GET", f"/api/v1/users/{two_tenants.b.user_id}", token=two_tenants.a.token
    )
    assert resp.status_code == 404, resp.text


async def test_users_patch_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    resp = await api(
        app,
        "PATCH",
        f"/api/v1/users/{two_tenants.b.user_id}",
        json={"full_name": "hackeado"},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_users_delete_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    resp = await api(
        app, "DELETE", f"/api/v1/users/{two_tenants.b.user_id}", token=two_tenants.a.token
    )
    assert resp.status_code == 404, resp.text


async def test_users_list_only_own_tenant(app: FastAPI, two_tenants: TwoTenants) -> None:
    resp = await api(app, "GET", "/api/v1/users", token=two_tenants.a.token)
    assert resp.status_code == 200, resp.text
    ids = [u["id"] for u in resp.json()["items"]]
    assert two_tenants.b.user_id not in ids
    assert two_tenants.a.user_id in ids


# --- rbac ---------------------------------------------------------------------


async def test_role_patch_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    role_b = await _seed_role(app, two_tenants.b)
    resp = await api(
        app,
        "PATCH",
        f"/api/v1/rbac/roles/{role_b}",
        json={"display_name": "hackeado"},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_role_delete_cross_tenant_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    role_b = await _seed_role(app, two_tenants.b)
    resp = await api(app, "DELETE", f"/api/v1/rbac/roles/{role_b}", token=two_tenants.a.token)
    assert resp.status_code == 404, resp.text


async def test_role_permission_assign_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants
) -> None:
    role_b = await _seed_role(app, two_tenants.b)
    perms = await api(app, "GET", "/api/v1/rbac/permissions", token=two_tenants.a.token)
    perm_id = perms.json()["items"][0]["id"]
    resp = await api(
        app,
        "POST",
        f"/api/v1/rbac/roles/{role_b}/permissions",
        json={"permission_id": perm_id},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


async def test_user_role_assign_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants, session_factory: async_sessionmaker
) -> None:
    user_b, _, _ = await create_member(session_factory, uuid.UUID(two_tenants.b.org_id))
    roles_a = await api(app, "GET", "/api/v1/rbac/roles", token=two_tenants.a.token)
    roles_body = roles_a.json()
    roles_list = roles_body.get("roles") or roles_body.get("items")
    role_a = roles_list[0]["id"]
    resp = await api(
        app,
        "POST",
        f"/api/v1/rbac/users/{user_b}/roles",
        json={"role_id": role_a},
        token=two_tenants.a.token,
    )
    assert resp.status_code == 404, resp.text


# --- audit ----------------------------------------------------------------------


async def test_audit_detail_cross_tenant_is_404(
    app: FastAPI, two_tenants: TwoTenants, session_factory: async_sessionmaker
) -> None:
    event_b = await _seed_audit_event(session_factory, two_tenants.b)
    resp = await api(app, "GET", f"/api/v1/audit/{event_b}", token=two_tenants.a.token)
    assert resp.status_code == 404, resp.text


async def test_audit_list_only_own_tenant(
    app: FastAPI, two_tenants: TwoTenants, session_factory: async_sessionmaker
) -> None:
    event_b = await _seed_audit_event(session_factory, two_tenants.b)
    resp = await api(app, "GET", "/api/v1/audit", token=two_tenants.a.token)
    assert resp.status_code == 200, resp.text
    ids = [item["id"] for item in resp.json()["items"]]
    assert str(event_b) not in ids
    assert all(i["tenant_id"] == two_tenants.a.org_id for i in resp.json()["items"])


# --- sessions -------------------------------------------------------------------


async def test_session_revoke_cross_user_is_404(app: FastAPI, two_tenants: TwoTenants) -> None:
    sessions_b = await api(app, "GET", "/api/v1/users/me/sessions", token=two_tenants.b.token)
    assert sessions_b.status_code == 200, sessions_b.text
    session_b = sessions_b.json()["items"][0]["id"]
    resp = await api(
        app, "DELETE", f"/api/v1/users/me/sessions/{session_b}", token=two_tenants.a.token
    )
    assert resp.status_code == 404, resp.text


# --- JWT identity -------------------------------------------------------------------


async def test_jwt_tenant_identity_cannot_be_spoofed(app: FastAPI, two_tenants: TwoTenants) -> None:
    """Tenant B's JWT always resolves B's context on tenant-scoped 'me' endpoints."""
    resp = await api(app, "GET", "/api/v1/organizations/me", token=two_tenants.b.token)
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == two_tenants.b.org_id

    resp_a = await api(app, "GET", "/api/v1/organizations/me", token=two_tenants.a.token)
    assert resp_a.json()["id"] == two_tenants.a.org_id
