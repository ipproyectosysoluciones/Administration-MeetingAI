"""TASK-040: POST /auth/register — org + tenant + org-admin + base role seeding.

Integration tests against a real PostgreSQL. Covers the happy path, duplicate
email rejection, and the non-negotiable "no platform super-admin via self-service"
rule (the role is forced to ``org_admin``).
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.organizations.models import Membership, Organization
from app.modules.rbac.models import Role, UserRole
from app.modules.users.models import User


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": f"admin-{uuid.uuid4()}@example.com",
        "password": "securePassword123",
        "full_name": "Juan Pérez",
        "organization_name": "Conjunto Residencial Los Pinos",
        "organization_slug": f"los-pinos-{uuid.uuid4().hex[:8]}",
    }
    payload.update(overrides)
    return payload


async def _post(app: FastAPI, path: str, json: dict[str, object]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=json)


async def test_register_creates_org_user_membership_and_returns_tokens(
    auth_app: FastAPI,
) -> None:
    resp = await _post(auth_app, "/api/v1/auth/register", _payload())

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"]
    assert body["user"]["email"]
    assert body["user"]["tenant_id"]
    assert body["user"]["mfa_enabled"] is False
    assert "organization.read" in body["user"]["permissions"]
    assert "refresh_token" in resp.cookies


async def test_register_bootstraps_tenant_and_org_admin_role(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    email = f"admin-{uuid.uuid4()}@example.com"
    resp = await _post(auth_app, "/api/v1/auth/register", _payload(email=email))
    assert resp.status_code == 201, resp.text
    user_id = resp.json()["user"]["id"]
    tenant_id = resp.json()["user"]["tenant_id"]

    async with session_factory() as session:
        user = await session.get(User, uuid.UUID(user_id))
        assert user is not None and user.email == email
        assert user.password_hash.startswith("$argon2id$")

        org = await session.get(Organization, uuid.UUID(tenant_id))
        assert org is not None and org.deleted_at is None

        membership = (
            await session.execute(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.organization_id == org.id,
                )
            )
        ).scalar_one()
        assert membership.role == "org_admin"

        user_role = (
            await session.execute(
                select(UserRole, Role.name)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    UserRole.user_id == user.id,
                    UserRole.organization_id == org.id,
                )
            )
        ).one()
        assert user_role.name == "org_admin"


async def test_register_rejects_duplicate_email(auth_app: FastAPI) -> None:
    payload = _payload()
    first = await _post(auth_app, "/api/v1/auth/register", payload)
    assert first.status_code == 201

    second = await _post(auth_app, "/api/v1/auth/register", payload)
    assert second.status_code == 409
    assert second.json()["code"] == "EMAIL_EXISTS"


async def test_register_cannot_create_super_admin(
    auth_app: FastAPI, session_factory: async_sessionmaker
) -> None:
    email = f"admin-{uuid.uuid4()}@example.com"
    resp = await _post(
        auth_app,
        "/api/v1/auth/register",
        _payload(email=email, organization_name="x", organization_slug=f"s-{uuid.uuid4().hex[:8]}"),
    )
    assert resp.status_code == 201

    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.email == email))).scalar_one()
        assert user.is_super_admin is False


async def test_register_rejects_missing_fields(auth_app: FastAPI) -> None:
    payload = _payload()
    del payload["email"]
    resp = await _post(auth_app, "/api/v1/auth/register", payload)
    assert resp.status_code == 422
