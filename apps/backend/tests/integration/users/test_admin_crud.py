"""TASK-050: tenant-scoped admin user management (GET/PATCH/DELETE /users and /users/{id}).

Covers tenant-scoped listing, single-user retrieval, admin update, and soft delete,
with the non-negotiable cross-tenant 404 and self/super-admin protections.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.users.models import User

from .conftest import _request, create_member, register


async def test_list_users_returns_only_current_tenant(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    admin_a_token = a["access_token"]

    resp = await _request(app, "GET", "/api/v1/users", token=admin_a_token)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    emails = [item["email"] for item in body["items"]]
    assert a["user"]["email"] in emails
    assert b["user"]["email"] not in emails
    assert all(item["id"] != b["user"]["id"] for item in body["items"])


async def test_list_users_includes_members_and_excludes_soft_deleted(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, member_email = await create_member(session_factory, tenant_a)

    resp = await _request(app, "GET", "/api/v1/users", token=token)
    assert resp.status_code == 200, resp.text
    emails = [item["email"] for item in resp.json()["items"]]
    assert member_email in emails
    assert a["user"]["email"] in emails

    # Soft-delete the member directly, then confirm they drop out of the listing.
    async with session_factory() as session:
        from datetime import UTC, datetime

        member = await session.get(User, member_id)
        member.deleted_at = datetime.now(UTC)
        await session.commit()

    resp = await _request(app, "GET", "/api/v1/users", token=token)
    emails = [item["email"] for item in resp.json()["items"]]
    assert member_email not in emails


async def test_get_user_in_tenant(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, member_email = await create_member(session_factory, tenant_a)

    resp = await _request(app, "GET", f"/api/v1/users/{member_id}", token=token)

    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == member_email


async def test_get_user_cross_tenant_returns_404(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    token_a = a["access_token"]
    # b's admin is in tenant B; a must see 404 (not 403).
    neighbor_id = uuid.UUID(b["user"]["id"])

    resp = await _request(app, "GET", f"/api/v1/users/{neighbor_id}", token=token_a)

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "USER_NOT_FOUND"


async def test_update_user_admin(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_a)

    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/users/{member_id}",
        json={"full_name": "Renamed Member", "is_active": False},
        token=token,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["full_name"] == "Renamed Member"
    assert resp.json()["is_active"] is False


async def test_update_user_cross_tenant_returns_404(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    token_a = a["access_token"]
    neighbor_id = uuid.UUID(b["user"]["id"])

    resp = await _request(
        app, "PATCH", f"/api/v1/users/{neighbor_id}", json={"full_name": "Hacked"}, token=token_a
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "USER_NOT_FOUND"


async def test_delete_user_soft_deletes(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_a)

    resp = await _request(app, "DELETE", f"/api/v1/users/{member_id}", token=token)

    assert resp.status_code == 200, resp.text
    assert resp.json()["message"] == "User deleted"
    assert resp.json()["deleted_at"]

    async with session_factory() as session:
        member = await session.get(User, member_id)
        assert member is not None  # soft-deleted, row preserved
        assert member.deleted_at is not None


async def test_delete_user_cross_tenant_returns_404(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    token_a = a["access_token"]
    neighbor_id = uuid.UUID(b["user"]["id"])

    resp = await _request(app, "DELETE", f"/api/v1/users/{neighbor_id}", token=token_a)

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "USER_NOT_FOUND"


async def test_delete_self_returns_403(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]
    self_id = uuid.UUID(a["user"]["id"])

    resp = await _request(app, "DELETE", f"/api/v1/users/{self_id}", token=token)

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "DELETE_NOT_ALLOWED"


async def test_delete_super_admin_returns_403(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    super_id, _ = await create_member(session_factory, tenant_a, is_super_admin=True)

    resp = await _request(app, "DELETE", f"/api/v1/users/{super_id}", token=token)

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "DELETE_NOT_ALLOWED"


async def test_soft_deleted_user_cannot_login(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, member_email = await create_member(session_factory, tenant_a)

    resp = await _request(app, "DELETE", f"/api/v1/users/{member_id}", token=token)
    assert resp.status_code == 200, resp.text

    login = await _request(
        app, "POST", "/api/v1/auth/login", json={"email": member_email, "password": "memberPass123"}
    )
    assert login.status_code in (401, 403)
