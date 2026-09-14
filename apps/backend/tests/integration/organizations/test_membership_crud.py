"""TASK-060 (membership slice): membership management with nullable property_id."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import PasswordHasher
from app.modules.organizations.models import Membership, Property
from app.modules.users.models import User

from .conftest import _request, create_member, register


async def _seed_property(
    session_factory: async_sessionmaker, tenant_id: uuid.UUID, name: str = "Torre A"
) -> uuid.UUID:
    async with session_factory() as session:
        prop = Property(organization_id=tenant_id, name=name)
        session.add(prop)
        await session.flush()
        prop_id = prop.id
        await session.commit()
        return prop_id


async def _make_user(session_factory: async_sessionmaker) -> uuid.UUID:
    async with session_factory() as session:
        user = User(
            email=f"target-{uuid.uuid4()}@example.com",
            password_hash=PasswordHasher().hash("targetPass123"),
            full_name="Target User",
        )
        session.add(user)
        await session.flush()
        user_id = user.id
        await session.commit()
        return user_id


async def _membership_id(
    session_factory: async_sessionmaker, user_id: uuid.UUID, tenant_id: uuid.UUID
) -> uuid.UUID:
    async with session_factory() as session:
        m = (
            await session.execute(
                select(Membership).where(
                    Membership.user_id == user_id,
                    Membership.organization_id == tenant_id,
                )
            )
        ).scalar_one()
        return m.id


async def test_create_membership_with_property(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    prop_id = await _seed_property(session_factory, tenant_a)
    target_id = await _make_user(session_factory)

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(target_id), "role": "resident", "property_id": str(prop_id)},
        token=a["access_token"],
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["property_id"] == str(prop_id)
    assert resp.json()["role"] == "resident"


async def test_create_membership_optional_property(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    target_id = await _make_user(session_factory)

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(target_id), "role": "resident"},
        token=a["access_token"],
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["property_id"] is None


async def test_create_membership_duplicate(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    target_id = await _make_user(session_factory)

    first = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(target_id), "role": "resident"},
        token=a["access_token"],
    )
    assert first.status_code == 201, first.text

    second = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(target_id), "role": "board_member"},
        token=a["access_token"],
    )

    assert second.status_code == 409, second.text
    assert second.json()["code"] == "MEMBERSHIP_EXISTS"


async def test_create_membership_user_not_found(app: FastAPI) -> None:
    a = await register(app)

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(uuid.uuid4()), "role": "resident"},
        token=a["access_token"],
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "USER_NOT_FOUND"


async def test_create_membership_property_not_in_tenant(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    b = await register(app)
    tenant_b = uuid.UUID(b["user"]["tenant_id"])
    prop_b = await _seed_property(session_factory, tenant_b, name="Torre B")
    target_id = await _make_user(session_factory)

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/memberships",
        json={"user_id": str(target_id), "role": "resident", "property_id": str(prop_b)},
        token=a["access_token"],
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "PROPERTY_NOT_FOUND"


async def test_list_memberships(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    _, member_email = await create_member(session_factory, tenant_a)

    resp = await _request(
        app, "GET", "/api/v1/organizations/me/memberships", token=a["access_token"]
    )

    assert resp.status_code == 200, resp.text
    emails = [item["user_email"] for item in resp.json()["items"]]
    assert member_email in emails


async def test_patch_membership(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_a)
    prop_id = await _seed_property(session_factory, tenant_a)
    mid = await _membership_id(session_factory, member_id, tenant_a)

    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/organizations/me/memberships/{mid}",
        json={"role": "board_member", "property_id": str(prop_id)},
        token=a["access_token"],
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "board_member"
    assert resp.json()["property_id"] == str(prop_id)


async def test_patch_membership_cross_tenant_404(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    b = await register(app)
    tenant_b = uuid.UUID(b["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_b)
    mid = await _membership_id(session_factory, member_id, tenant_b)

    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/organizations/me/memberships/{mid}",
        json={"role": "hacked"},
        token=a["access_token"],
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "MEMBERSHIP_NOT_FOUND"


async def test_delete_membership(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_a)
    mid = await _membership_id(session_factory, member_id, tenant_a)

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/me/memberships/{mid}", token=a["access_token"]
    )
    assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        m = await session.get(Membership, mid)
        assert m.deleted_at is not None


async def test_delete_membership_cross_tenant_404(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    b = await register(app)
    tenant_b = uuid.UUID(b["user"]["tenant_id"])
    member_id, _ = await create_member(session_factory, tenant_b)
    mid = await _membership_id(session_factory, member_id, tenant_b)

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/me/memberships/{mid}", token=a["access_token"]
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "MEMBERSHIP_NOT_FOUND"


async def test_delete_membership_self_forbidden(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    admin_id = uuid.UUID(a["user"]["id"])
    mid = await _membership_id(session_factory, admin_id, tenant_a)

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/me/memberships/{mid}", token=a["access_token"]
    )

    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "REMOVE_NOT_ALLOWED"
