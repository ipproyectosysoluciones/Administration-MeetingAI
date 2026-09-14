"""TASK-060 (org-CRUD slice): platform org creation + tenant-scoped org CRUD.

Covers super-admin-only organization creation, tenant-scoped read/update, soft-delete
with cascade to properties/memberships, and the resulting loss of tenant access.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Settings
from app.modules.organizations.models import Membership, Organization, Property
from app.modules.users.models import User

from .conftest import _request, create_member, create_super_admin, mint_token, register

# -- creation (super-admin only) ---------------------------------------------


async def test_create_organization_super_admin(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    _, token = await create_super_admin(session_factory, settings)
    slug = f"nueva-{uuid.uuid4().hex[:8]}"

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations",
        json={"name": "Nueva Organización", "slug": slug, "description": "Descripción"},
        token=token,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Nueva Organización"
    assert body["slug"] == slug
    assert body["description"] == "Descripción"
    assert body["id"]


async def test_create_organization_non_super_admin_forbidden(app: FastAPI) -> None:
    a = await register(app)  # org_admin, not a platform super-admin

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations",
        json={"name": "X", "slug": "x-123"},
        token=a["access_token"],
    )

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "SUPER_ADMIN_REQUIRED"


async def test_create_organization_slug_conflict(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    _, token = await create_super_admin(session_factory, settings)
    slug = f"slug-{uuid.uuid4().hex[:8]}"

    first = await _request(
        app, "POST", "/api/v1/organizations", json={"name": "A", "slug": slug}, token=token
    )
    assert first.status_code == 201, first.text

    second = await _request(
        app, "POST", "/api/v1/organizations", json={"name": "B", "slug": slug}, token=token
    )

    assert second.status_code == 409, second.text
    assert second.json()["code"] == "SLUG_EXISTS"


async def test_create_organization_requires_auth(app: FastAPI) -> None:
    resp = await _request(app, "POST", "/api/v1/organizations", json={"name": "X", "slug": "y"})
    assert resp.status_code == 401


# -- tenant-scoped read/update ------------------------------------------------


async def test_get_me_returns_own_organization(app: FastAPI) -> None:
    a = await register(app)

    resp = await _request(app, "GET", "/api/v1/organizations/me", token=a["access_token"])

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == a["user"]["tenant_id"]
    assert body["name"] == "Conjunto Los Pinos"


async def test_get_me_requires_auth(app: FastAPI) -> None:
    resp = await _request(app, "GET", "/api/v1/organizations/me")
    assert resp.status_code == 401


async def test_update_me(app: FastAPI) -> None:
    a = await register(app)

    resp = await _request(
        app,
        "PATCH",
        "/api/v1/organizations/me",
        json={
            "name": "Renamed Org",
            "description": "Nueva descripción",
            "settings": {"timezone": "America/Bogota"},
        },
        token=a["access_token"],
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Renamed Org"
    assert body["description"] == "Nueva descripción"
    assert body["settings"] == {"timezone": "America/Bogota"}


async def test_update_me_slug_immutable(app: FastAPI) -> None:
    a = await register(app)
    before = await _request(app, "GET", "/api/v1/organizations/me", token=a["access_token"])
    original_slug = before.json()["slug"]

    resp = await _request(
        app,
        "PATCH",
        "/api/v1/organizations/me",
        json={"slug": "hacked"},
        token=a["access_token"],
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == original_slug


async def test_update_me_forbidden_without_permission(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    guest_id, _ = await create_member(session_factory, tenant_a, role="guest")
    guest_token = await mint_token(settings, guest_id)

    resp = await _request(
        app, "PATCH", "/api/v1/organizations/me", json={"name": "Hacked"}, token=guest_token
    )

    assert resp.status_code == 403, resp.text


# -- soft delete with cascade ------------------------------------------------


async def test_delete_organization_soft_deletes_and_cascades(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    _, super_token = await create_super_admin(session_factory, settings)

    # Seed a property + a member with a property-scoped membership directly (the
    # property/membership endpoints land in the next slice).
    async with session_factory() as session:
        prop = Property(organization_id=tenant_a, name="Torre A")
        session.add(prop)
        await session.flush()
        member = User(
            email=f"m-{uuid.uuid4()}@example.com",
            password_hash="x-not-used",
            full_name="Member",
        )
        session.add(member)
        await session.flush()
        session.add(
            Membership(
                user_id=member.id,
                organization_id=tenant_a,
                role="resident",
                property_id=prop.id,
            )
        )
        await session.commit()
        prop_id = prop.id

        resp = await _request(app, "DELETE", f"/api/v1/organizations/{tenant_a}", token=super_token)
        assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        org = await session.get(Organization, tenant_a)
        assert org.deleted_at is not None
        prop_row = await session.get(Property, prop_id)
        assert prop_row.deleted_at is not None
        active_memberships = (
            (
                await session.execute(
                    select(Membership).where(
                        Membership.organization_id == tenant_a,
                        Membership.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert active_memberships == []


async def test_delete_organization_revokes_tenant_access(
    app: FastAPI, session_factory: async_sessionmaker, settings: Settings
) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    admin_token = a["access_token"]
    _, super_token = await create_super_admin(session_factory, settings)

    resp = await _request(app, "DELETE", f"/api/v1/organizations/{tenant_a}", token=super_token)
    assert resp.status_code == 200, resp.text

    # The admin's membership is now soft-deleted → tenant resolution fails (403).
    resp2 = await _request(app, "GET", "/api/v1/organizations/me", token=admin_token)
    assert resp2.status_code == 403, resp2.text


async def test_delete_organization_non_super_admin_forbidden(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    tenant_b = uuid.UUID(b["user"]["tenant_id"])

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/{tenant_b}", token=a["access_token"]
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "SUPER_ADMIN_REQUIRED"
