"""Unit tests for permission resolution and require_permission (TASK-031).

Covers `architecture.md` §5.3 (union resolution) and the 401 vs 403 semantics of
the `require_permission` FastAPI dependency. Test priority 1 (authorization) and
2 (tenant isolation).
"""

from __future__ import annotations

import uuid
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import (
    AuthContext,
    Role,
    require_permission,
    resolve_permissions,
)
from app.core.exceptions import TenantResolutionError
from app.core.security import JWTService


class FakeResolver:
    """Returns a fixed AuthContext per user; raises KeyError for unknown users."""

    def __init__(self, contexts: dict[uuid.UUID, AuthContext]) -> None:
        self._contexts = contexts

    async def resolve_context(self, user_id: uuid.UUID) -> AuthContext:
        return self._contexts[user_id]


class NoMembershipResolver:
    async def resolve_context(self, user_id: uuid.UUID) -> AuthContext:
        raise TenantResolutionError()


def build_app(jwt_service: JWTService, resolver: object) -> FastAPI:
    app = FastAPI()
    app.state.jwt_service = jwt_service
    app.state.authorization_resolver = resolver

    @app.get("/protected")
    async def protected(
        ctx: Annotated[AuthContext, Depends(require_permission("user.read"))],
    ) -> dict:
        return {"ok": True, "tid": str(ctx.tenant_id) if ctx.tenant_id else None}

    return app


# ---------------------------------------------------------------------------
# Union resolution (architecture.md §5.3)
# ---------------------------------------------------------------------------
class TestResolvePermissions:
    def test_union_across_roles(self) -> None:
        roles = [
            Role(name="resident", permissions=frozenset({"organization.read", "user.read"})),
            Role(name="reviewer", permissions=frozenset({"user.read", "minutes.review"})),
        ]
        assert resolve_permissions(roles) == frozenset(
            {"organization.read", "user.read", "minutes.review"}
        )

    def test_empty_roles_yields_empty_set(self) -> None:
        assert resolve_permissions([]) == frozenset()


# ---------------------------------------------------------------------------
# require_permission dependency (401 vs 403)
# ---------------------------------------------------------------------------
class TestRequirePermission:
    @pytest.fixture
    def jwt_service(self, rsa_keys: tuple[str, str]) -> JWTService:
        private_pem, public_pem = rsa_keys
        return JWTService(Settings(jwt_private_key=private_pem, jwt_public_key=public_pem))

    @pytest.fixture
    def user_id(self) -> uuid.UUID:
        return uuid.uuid4()

    @pytest.fixture
    def allowed_context(self, user_id: uuid.UUID) -> AuthContext:
        return AuthContext(
            user_id=user_id,
            tenant_id=uuid.uuid4(),
            permissions=frozenset({"user.read"}),
            is_super_admin=False,
        )

    @pytest.fixture
    def denied_context(self, user_id: uuid.UUID) -> AuthContext:
        return AuthContext(
            user_id=user_id,
            tenant_id=uuid.uuid4(),
            permissions=frozenset({"organization.read"}),
            is_super_admin=False,
        )

    def _token(self, jwt_service: JWTService, user_id: uuid.UUID) -> str:
        return jwt_service.create_access_token(user_id, uuid.uuid4(), [])

    def test_denies_unauthenticated(self, jwt_service: JWTService, user_id: uuid.UUID) -> None:
        app = build_app(jwt_service, FakeResolver({}))
        with TestClient(app) as client:
            # No Authorization header at all.
            assert client.get("/protected").status_code == 401

    def test_denies_invalid_token(
        self, jwt_service: JWTService, allowed_context: AuthContext, user_id: uuid.UUID
    ) -> None:
        app = build_app(jwt_service, FakeResolver({user_id: allowed_context}))
        with TestClient(app) as client:
            resp = client.get("/protected", headers={"Authorization": "Bearer nonsense"})
            assert resp.status_code == 401

    def test_denies_when_missing_permission(
        self, jwt_service: JWTService, denied_context: AuthContext, user_id: uuid.UUID
    ) -> None:
        app = build_app(jwt_service, FakeResolver({user_id: denied_context}))
        with TestClient(app) as client:
            resp = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {self._token(jwt_service, user_id)}"},
            )
            assert resp.status_code == 403

    def test_allows_when_permission_granted(
        self, jwt_service: JWTService, allowed_context: AuthContext, user_id: uuid.UUID
    ) -> None:
        app = build_app(jwt_service, FakeResolver({user_id: allowed_context}))
        with TestClient(app) as client:
            resp = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {self._token(jwt_service, user_id)}"},
            )
            assert resp.status_code == 200
            assert resp.json()["ok"] is True

    def test_super_admin_bypasses_permission_check(
        self, jwt_service: JWTService, user_id: uuid.UUID
    ) -> None:
        super_admin = AuthContext(
            user_id=user_id,
            tenant_id=None,
            permissions=frozenset(),
            is_super_admin=True,
        )
        app = build_app(jwt_service, FakeResolver({user_id: super_admin}))
        with TestClient(app) as client:
            resp = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {self._token(jwt_service, user_id)}"},
            )
            assert resp.status_code == 200

    def test_no_active_membership_returns_403(
        self, jwt_service: JWTService, user_id: uuid.UUID
    ) -> None:
        app = build_app(jwt_service, NoMembershipResolver())
        with TestClient(app) as client:
            resp = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {self._token(jwt_service, user_id)}"},
            )
            assert resp.status_code == 403
