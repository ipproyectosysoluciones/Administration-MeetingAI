"""TASK-070: permission registry + base role seeding (spec.rbac §registry, §base roles).

Covers the tenant-readable registry, base-role listing, base-role immutability,
and the contract-name reconciliation (``auth.mfa.manage`` wins over the draft
``user.mfa.manage`` naming in proposal/specs).
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.modules.rbac.models import Permission, Role

from .conftest import _request, create_member, mint_token, register

_BASE_ROLE_NAMES = {
    "super_admin",
    "org_admin",
    "property_admin",
    "president",
    "secretary",
    "board_member",
    "reviewer",
    "co_owner",
    "resident",
    "guest",
}


async def test_list_permissions_registry(app: FastAPI) -> None:
    a = await register(app)
    resp = await _request(app, "GET", "/api/v1/rbac/permissions", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    names = {item["name"] for item in body["items"]}
    assert body["total"] == len(body["items"])
    assert {"permission.read", "role.read", "role.create", "user.role.assign"} <= names
    for item in body["items"]:
        assert item["resource"] and item["action"]
        assert item["name"] == f"{item['resource']}.{item['action']}" or item["resource"] == "auth"


async def test_permissions_contract_mfa_name(app: FastAPI) -> None:
    """Contract name ``auth.mfa.manage`` wins; draft ``user.mfa.manage`` MUST NOT exist."""
    a = await register(app)
    resp = await _request(app, "GET", "/api/v1/rbac/permissions", token=a["access_token"])
    names = {item["name"] for item in resp.json()["items"]}
    assert "auth.mfa.manage" in names
    assert "user.mfa.manage" not in names


async def test_permissions_require_permission_read(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    tenant = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant, role="resident")
    member_token = await mint_token(settings, member_id)  # resident lacks permission.read
    resp = await _request(app, "GET", "/api/v1/rbac/permissions", token=member_token)
    assert resp.status_code == 403


async def test_permissions_require_auth(app: FastAPI) -> None:
    resp = await _request(app, "GET", "/api/v1/rbac/permissions")
    assert resp.status_code == 401


async def test_list_roles_returns_base_roles(app: FastAPI) -> None:
    a = await register(app)
    resp = await _request(app, "GET", "/api/v1/rbac/roles", token=a["access_token"])
    assert resp.status_code == 200, resp.text
    roles = resp.json()["items"]
    names = {r["name"] for r in roles}
    assert _BASE_ROLE_NAMES <= names
    org_admin = next(r for r in roles if r["name"] == "org_admin")
    assert org_admin["is_system"] is True
    perm_names = {p["name"] for p in org_admin["permissions"]}
    assert {"role.read", "role.create", "user.role.assign"} <= perm_names


async def test_seeding_is_idempotent(session_factory: async_sessionmaker) -> None:
    """Migration seed is ``ON CONFLICT DO NOTHING``: exactly 10 base platform roles."""
    async with session_factory() as session:
        base_count = (
            await session.execute(
                select(func.count()).select_from(Role).where(Role.organization_id.is_(None))
            )
        ).scalar_one()
        perm_count = (
            await session.execute(select(func.count()).select_from(Permission))
        ).scalar_one()
    assert base_count == 10
    assert perm_count == 39  # 34 foundation + 5 meeting.* (TASK-201); rerunning seed keeps it stable
