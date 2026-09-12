"""Unit tests for the tenant-context resolution chain (TASK-030).

Covers `architecture.md` §3: the active membership (→ tenant) is derived from
the authenticated user's memberships, never from a request-supplied `tenant_id`.
Test priority 2 (tenant isolation) — these are the primitive-level seams.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.core.dependencies import Membership, resolve_active_membership


def membership(
    *,
    organization_id: uuid.UUID | None = None,
    role: str = "resident",
    created_at: datetime | None = None,
    deleted_at: datetime | None = None,
    organization_deleted_at: datetime | None = None,
) -> Membership:
    return Membership(
        organization_id=organization_id or uuid.uuid4(),
        role=role,
        property_id=None,
        created_at=created_at or datetime.now(UTC),
        deleted_at=deleted_at,
        organization_deleted_at=organization_deleted_at,
    )


class TestResolveActiveMembership:
    def test_returns_most_recent_active_membership(self) -> None:
        older = membership(created_at=datetime.now(UTC) - timedelta(days=2))
        newest = membership(created_at=datetime.now(UTC))
        resolved = resolve_active_membership([older, newest])
        assert resolved is not None
        assert resolved.organization_id == newest.organization_id

    def test_ignores_deleted_membership(self) -> None:
        active = membership(created_at=datetime.now(UTC) - timedelta(days=1))
        deleted = membership(created_at=datetime.now(UTC), deleted_at=datetime.now(UTC))
        resolved = resolve_active_membership([active, deleted])
        assert resolved is not None
        assert resolved.organization_id == active.organization_id

    def test_ignores_membership_of_deleted_organization(self) -> None:
        active = membership(created_at=datetime.now(UTC) - timedelta(days=1))
        in_deleted_org = membership(
            created_at=datetime.now(UTC), organization_deleted_at=datetime.now(UTC)
        )
        resolved = resolve_active_membership([active, in_deleted_org])
        assert resolved is not None
        assert resolved.organization_id == active.organization_id

    def test_returns_none_for_empty(self) -> None:
        assert resolve_active_membership([]) is None

    def test_returns_none_when_all_excluded(self) -> None:
        soft_deleted = membership(deleted_at=datetime.now(UTC))
        deleted_org = membership(organization_deleted_at=datetime.now(UTC))
        assert resolve_active_membership([soft_deleted, deleted_org]) is None

    def test_tenant_is_derived_from_membership_not_request(self) -> None:
        """The resolution function has no request/tenant input; the tenant can only
        come from the membership data itself (never a client-supplied id)."""
        org_id = uuid.uuid4()
        only = membership(organization_id=org_id)
        resolved = resolve_active_membership([only])
        assert resolved is not None
        assert resolved.organization_id == org_id
