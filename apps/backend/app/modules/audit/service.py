"""Audit service: event recording and tenant-scoped query (api-contract.md §6).

Provides:
- AuditService.record(): explicit capture on critical ops (login, role/permission changes).
- AuditService.query(): paginated+filtered audit log per tenant.
- AuditService.get(): single event detail per tenant.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.modules.audit.models import AuditEvent


class AuditService:
    """Audit service with explicit capture + tenant-scoped query."""

    # -- recording ------------------------------------------------------------

    @staticmethod
    def _make_event(
        actor_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Construct an AuditEvent with normalized metadata dict."""
        return AuditEvent(
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            timestamp=datetime.now(UTC),
            ip=ip,
            user_agent=user_agent,
            metadata_json=metadata or {},
        )

    @classmethod
    async def record(
        cls,
        session,
        actor_user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        action: str,
        resource: str,
        resource_id: uuid.UUID | None,
        ip: str | None,
        user_agent: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Explicitly record an audit event (best-effort; never blocks primary op).

        Best-effort flush; do NOT commit or roll back the primary tx.
        The caller's transaction owns commit/rollback.
        """
        event = cls._make_event(
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip=ip,
            user_agent=user_agent,
            metadata=metadata,
        )
        session.add(event)
        try:
            await session.flush()
        except Exception:
            # Never let audit failure cascade to the primary operation.
            pass
        return event

    # -- query ----------------------------------------------------------------

    @classmethod
    async def query(
        cls,
        session,
        tenant_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        resource: str | None = None,
        resource_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        ip: str | None = None,
    ) -> dict[str, Any]:
        """Paginated, filterable audit log for the given tenant.

        Filters per api-contract.md §6.1:
        - action (exact match)
        - resource (exact match)
        - resource_id (exact match, UUID)
        - actor_user_id (exact match)
        - date_from / date_to (ISO 8601, inclusive)
        - ip (INET, exact match)
        """
        page_size = min(page_size, 100)  # api-contract.md §6 max

        stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)

        if action is not None:
            stmt = stmt.where(AuditEvent.action == action)
        if resource is not None:
            stmt = stmt.where(AuditEvent.resource == resource)
        if resource_id is not None:
            stmt = stmt.where(AuditEvent.resource_id == resource_id)
        if actor_user_id is not None:
            stmt = stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if date_from is not None:
            stmt = stmt.where(AuditEvent.timestamp >= date_from)
        if date_to is not None:
            stmt = stmt.where(AuditEvent.timestamp <= date_to)
        if ip is not None:
            stmt = stmt.where(AuditEvent.ip == ip)

        # Count total before pagination
        count_stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
        if action is not None:
            count_stmt = count_stmt.where(AuditEvent.action == action)
        if resource is not None:
            count_stmt = count_stmt.where(AuditEvent.resource == resource)
        if resource_id is not None:
            count_stmt = count_stmt.where(AuditEvent.resource_id == resource_id)
        if actor_user_id is not None:
            count_stmt = count_stmt.where(AuditEvent.actor_user_id == actor_user_id)
        if date_from is not None:
            count_stmt = count_stmt.where(AuditEvent.timestamp >= date_from)
        if date_to is not None:
            count_stmt = count_stmt.where(AuditEvent.timestamp <= date_to)
        if ip is not None:
            count_stmt = count_stmt.where(AuditEvent.ip == ip)

        # Apply ordering and pagination
        stmt = stmt.order_by(AuditEvent.timestamp.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        rows = (await session.execute(stmt)).scalars().all()
        total = (await session.execute(count_stmt)).scalar_one()

        pages: int = (total + page_size - 1) // page_size if total else 1

        items = [
            {
                "id": str(row.id),
                "actor_user_id": str(row.actor_user_id),
                "actor_email": None,
                "tenant_id": str(row.tenant_id),
                "action": row.action,
                "resource": row.resource,
                "resource_id": str(row.resource_id) if row.resource_id else None,
                "timestamp": row.timestamp,
                "ip": str(row.ip) if row.ip else None,
                "user_agent": row.user_agent,
                "metadata": row.metadata_json,
            }
            for row in rows
        ]

        result: dict[str, Any] = {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
        result["pages"] = pages
        return result

    # -- get single event -----------------------------------------------------

    @classmethod
    async def get(
        cls,
        session,
        tenant_id: uuid.UUID,
        event_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Retrieve a single audit event for the given tenant.

        Returns None when event not in current tenant (AUDIT_EVENT_NOT_FOUND).
        """
        stmt = select(AuditEvent).where(
            AuditEvent.tenant_id == tenant_id,
            AuditEvent.id == event_id,
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return {
            "id": str(row.id),
            "actor_user_id": str(row.actor_user_id),
            "actor_email": None,
            "tenant_id": str(row.tenant_id),
            "action": row.action,
            "resource": row.resource,
            "resource_id": str(row.resource_id) if row.resource_id else None,
            "timestamp": row.timestamp,
            "ip": str(row.ip) if row.ip else None,
            "user_agent": row.user_agent,
            "metadata": row.metadata_json,
        }
