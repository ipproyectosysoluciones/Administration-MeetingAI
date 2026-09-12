"""FastAPI dependency primitives: tenant context and authorization.

Houses the resolution chain from `architecture.md` §3 / §5 — the tenant is always
derived from the authenticated user's active membership, never from a
request-supplied ``tenant_id`` (IDOR prevention; `reunionai-multitenant-security`).

The pure resolution functions (``resolve_active_membership``, ``resolve_permissions``)
are the unit-testable heart of the chain; the DB-backed lookups behind them are
wired in the users/rbac module repositories (later PRs). ``require_permission``
composes JWT authentication (``core.security.JWTService``) with an injected
``AuthorizationResolver`` so it stays testable without the ORM models.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from fastapi import HTTPException, Request

from app.core.exceptions import (
    ExpiredTokenError,
    InvalidTokenError,
    TenantResolutionError,
)
from app.core.security import JWTService


@dataclass(frozen=True)
class Membership:
    """A user's membership in an organization (tenant).

    ``organization_deleted_at`` is the *organization's* soft-delete timestamp,
    carried on the row so active-membership resolution can exclude memberships of
    soft-deleted organizations without a second lookup (architecture.md §3.3).
    """

    organization_id: uuid.UUID
    role: str
    property_id: uuid.UUID | None
    created_at: datetime
    deleted_at: datetime | None
    organization_deleted_at: datetime | None


def resolve_active_membership(memberships: Iterable[Membership]) -> Membership | None:
    """Return the active membership, or ``None`` if none qualify.

    Per `architecture.md` §3.3 (MVP rule): the most recent membership by
    ``created_at`` where both the membership and its organization are not
    soft-deleted. The caller never supplies a ``tenant_id`` — the tenant root is
    ``Membership.organization_id``.
    """
    active = [m for m in memberships if m.deleted_at is None and m.organization_deleted_at is None]
    if not active:
        return None
    return max(active, key=lambda m: m.created_at)


@dataclass(frozen=True)
class Role:
    """A role and the permissions it grants (union-resolution input, §5.3)."""

    name: str
    permissions: frozenset[str]


def resolve_permissions(roles: Iterable[Role]) -> frozenset[str]:
    """Union of permissions across roles (`architecture.md` §5.3).

    Permissions are additive (no deny rules); tenant scoping happens upstream when
    the repository selects roles for a user in a tenant.
    """
    union: set[str] = set()
    for role in roles:
        union |= role.permissions
    return frozenset(union)


@dataclass(frozen=True)
class AuthContext:
    """Authenticated identity + resolved tenant + effective permissions."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    permissions: frozenset[str]
    is_super_admin: bool = False

    def has_permission(self, permission: str) -> bool:
        """Super-admin is a wildcard; otherwise presence in the union set."""
        return self.is_super_admin or permission in self.permissions


class AuthorizationResolver(Protocol):
    """Resolves an AuthContext from a user id (DB lookup, wired in PR-4/5).

    The real implementation composes ``resolve_active_membership`` (tenant) and
    ``resolve_permissions`` over repository data; this primitive layer keeps the
    lookup behind a protocol so ``require_permission`` is testable without ORM
    models. May raise ``TenantResolutionError`` when no active membership exists.
    """

    async def resolve_context(self, user_id: uuid.UUID) -> AuthContext: ...


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if header is None:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def require_permission(permission: str) -> Callable[[Request], Awaitable[AuthContext]]:
    """FastAPI dependency enforcing ``resource.action`` (401 vs 403).

    Semantics (`architecture.md` §2.1 / §5.3, `api-contract.md` §1):

    - missing/invalid/expired token → 401 (unauthenticated);
    - no active membership → 403 (authenticated, no tenant scope);
    - permission absent from the union → 403 (unauthorized).

    The tenant/permissions are re-resolved from the injected resolver on every
    request (never trusted from the token's ``perm`` hint — §4.1).
    """

    async def dependency(request: Request) -> AuthContext:
        jwt_service: JWTService = request.app.state.jwt_service
        resolver: AuthorizationResolver = request.app.state.authorization_resolver
        token = _bearer_token(request)
        if token is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt_service.decode_access_token(token)
        except (InvalidTokenError, ExpiredTokenError) as exc:
            raise HTTPException(status_code=401, detail="Not authenticated") from exc
        user_id = uuid.UUID(payload["sub"])
        try:
            context = await resolver.resolve_context(user_id)
        except TenantResolutionError as exc:
            raise HTTPException(status_code=403, detail="No active membership") from exc
        if not context.has_permission(permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return context

    return dependency


__all__ = [
    "AuthContext",
    "AuthorizationResolver",
    "Membership",
    "Role",
    "require_permission",
    "resolve_active_membership",
    "resolve_permissions",
]
