"""TASK-046: mandatory MFA for administrative roles.

Integration tests against PostgreSQL. A user holding Super Admin, Organization Admin,
or Property Admin (data-model §4) must not receive full tokens at login until MFA is
enrolled (403 ``MFA_REQUIRED_FOR_ROLE``); non-administrative users are unaffected.
The role check reads the authoritative ``user_roles`` → ``roles`` assignment (the
``membership.role`` string is not used for authorization).
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.rbac.models import Role, UserRole
from app.modules.users.models import User


def _payload(**overrides: str) -> dict[str, str]:
    payload: dict[str, str] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Juan Pérez",
        "organization_name": "Conjunto Residencial Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    return payload


async def _register(auth_app: FastAPI, payload: dict[str, str]) -> dict[str, Any]:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()


async def _login(auth_app: FastAPI, email: str, password: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=auth_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/v1/auth/login", json={"email": email, "password": password})


async def _demote_to_resident(
    session_factory: async_sessionmaker, user_id: uuid.UUID, organization_id: uuid.UUID
) -> None:
    """Replace every role assignment with the non-admin ``resident`` base role."""
    async with session_factory() as db:
        resident_role_id = (
            await db.execute(
                select(Role.id).where(Role.name == "resident", Role.organization_id.is_(None))
            )
        ).scalar_one()
        await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
        db.add(UserRole(user_id=user_id, role_id=resident_role_id, organization_id=organization_id))
        await db.commit()


async def _grant_role(
    session_factory: async_sessionmaker,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    role_name: str,
) -> None:
    """Assign an admin role; for ``super_admin`` set the platform flag instead."""
    async with session_factory() as db:
        if role_name == "super_admin":
            user = await db.get(User, user_id)
            user.is_super_admin = True
        else:
            role_id = (
                await db.execute(
                    select(Role.id).where(Role.name == role_name, Role.organization_id.is_(None))
                )
            ).scalar_one()
            await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
            db.add(UserRole(user_id=user_id, role_id=role_id, organization_id=organization_id))
        await db.commit()


@pytest.mark.parametrize("role_name", ["org_admin", "property_admin", "super_admin"])
async def test_admin_login_without_mfa_is_blocked(
    auth_app: FastAPI, session_factory: async_sessionmaker, role_name: str
) -> None:
    payload = _payload()
    body = await _register(auth_app, payload)
    user_id = uuid.UUID(str(body["user"]["id"]))
    organization_id = uuid.UUID(str(body["user"]["tenant_id"]))

    if role_name != "org_admin":
        await _grant_role(session_factory, user_id, organization_id, role_name)

    login = await _login(auth_app, payload["email"], payload["password"])

    assert login.status_code == 403, login.text
    assert login.json()["code"] == "MFA_REQUIRED_FOR_ROLE"
    assert "access_token" not in login.json()


async def test_non_admin_login_is_unaffected(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    payload = _payload()
    body = await _register(auth_app, payload)
    user_id = uuid.UUID(str(body["user"]["id"]))
    organization_id = uuid.UUID(str(body["user"]["tenant_id"]))

    await _demote_to_resident(session_factory, user_id, organization_id)

    login = await _login(auth_app, payload["email"], payload["password"])

    assert login.status_code == 200, login.text
    assert login.json()["access_token"]
