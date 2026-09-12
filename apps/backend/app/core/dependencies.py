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
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime


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


__all__ = ["Membership", "resolve_active_membership"]
