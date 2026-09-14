"""TASK-060 (property slice): tenant-scoped property/group CRUD."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.organizations.models import Membership, Property
from app.modules.users.models import User

from .conftest import _request, register


async def _seed_property(
    session_factory: async_sessionmaker, tenant_id: uuid.UUID, *, name: str = "Torre A"
) -> uuid.UUID:
    async with session_factory() as session:
        prop = Property(organization_id=tenant_id, name=name)
        session.add(prop)
        await session.flush()
        prop_id = prop.id
        await session.commit()
        return prop_id


async def test_create_property(app: FastAPI) -> None:
    a = await register(app)

    resp = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/properties",
        json={"name": "Torre A", "code": "TORRE-A", "description": "Torre principal"},
        token=a["access_token"],
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Torre A"
    assert body["code"] == "TORRE-A"


async def test_create_property_code_conflict(app: FastAPI) -> None:
    a = await register(app)
    token = a["access_token"]

    first = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/properties",
        json={"name": "Torre A", "code": "DUP"},
        token=token,
    )
    assert first.status_code == 201, first.text

    second = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/properties",
        json={"name": "Torre B", "code": "DUP"},
        token=token,
    )

    assert second.status_code == 409, second.text
    assert second.json()["code"] == "PROPERTY_CODE_EXISTS"


async def test_list_properties(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    await _seed_property(session_factory, tenant_a, name="Torre A")

    resp = await _request(
        app, "GET", "/api/v1/organizations/me/properties", token=a["access_token"]
    )

    assert resp.status_code == 200, resp.text
    names = [item["name"] for item in resp.json()["items"]]
    assert "Torre A" in names


async def test_patch_property(app: FastAPI, session_factory: async_sessionmaker) -> None:
    a = await register(app)
    tenant_a = uuid.UUID(a["user"]["tenant_id"])
    prop_id = await _seed_property(session_factory, tenant_a)

    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/organizations/me/properties/{prop_id}",
        json={"name": "Torre Renamed", "code": "NEW"},
        token=a["access_token"],
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Torre Renamed"
    assert resp.json()["code"] == "NEW"


async def test_patch_property_cross_tenant_404(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    b = await register(app)
    tenant_b = uuid.UUID(b["user"]["tenant_id"])
    prop_id = await _seed_property(session_factory, tenant_b)

    resp = await _request(
        app,
        "PATCH",
        f"/api/v1/organizations/me/properties/{prop_id}",
        json={"name": "Hacked"},
        token=a["access_token"],
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "PROPERTY_NOT_FOUND"


async def test_delete_property_soft_deletes_and_nulls_memberships(
    app: FastAPI, session_factory: async_sessionmaker
) -> None:
    a = await register(app)
    token = a["access_token"]
    tenant_a = uuid.UUID(a["user"]["tenant_id"])

    async with session_factory() as session:
        prop = Property(organization_id=tenant_a, name="Torre A")
        session.add(prop)
        await session.flush()
        member = User(
            email=f"m-{uuid.uuid4()}@example.com", password_hash="x-not-used", full_name="M"
        )
        session.add(member)
        await session.flush()
        session.add(
            Membership(
                user_id=member.id, organization_id=tenant_a, role="resident", property_id=prop.id
            )
        )
        await session.commit()
        prop_id = prop.id
        member_id = member.id

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/me/properties/{prop_id}", token=token
    )
    assert resp.status_code == 200, resp.text

    async with session_factory() as session:
        prop = await session.get(Property, prop_id)
        assert prop.deleted_at is not None
        m = (
            await session.execute(
                select(Membership).where(
                    Membership.user_id == member_id,
                    Membership.organization_id == tenant_a,
                )
            )
        ).scalar_one()
        assert m.property_id is None


async def test_delete_property_cross_tenant_404(app: FastAPI) -> None:
    a = await register(app)
    b = await register(app)
    create = await _request(
        app,
        "POST",
        "/api/v1/organizations/me/properties",
        json={"name": "Torre B"},
        token=b["access_token"],
    )
    assert create.status_code == 201, create.text
    prop_id = create.json()["id"]

    resp = await _request(
        app, "DELETE", f"/api/v1/organizations/me/properties/{prop_id}", token=a["access_token"]
    )

    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "PROPERTY_NOT_FOUND"
