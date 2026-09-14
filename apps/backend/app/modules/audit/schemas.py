"""Pydantic request/response models for the audit module (api-contract.md §6)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventBase(BaseModel):
    """Base audit event fields shared across schemas."""

    id: str
    actor_user_id: str
    actor_email: str | None
    tenant_id: str
    action: str
    resource: str
    resource_id: str | None
    timestamp: datetime
    ip: str | None
    user_agent: str | None
    metadata: dict[str, Any]


class AuditEventCreate(BaseModel):
    """Schema for creating an audit event (internal use)."""

    actor_user_id: str
    tenant_id: str
    action: str
    resource: str
    resource_id: str | None
    ip: str | None
    user_agent: str | None
    metadata: dict[str, Any] = {}


class AuditEventQuery(BaseModel):
    """Query parameters for GET /audet.

    Corresponds to api-contract.md §6.1 query params.
    """

    action: str | None = None
    resource: str | None = None
    resource_id: str | None = None
    actor_user_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    ip: str | None = None


class AuditEventQueryParams:
    """Raw query parameter extraction for FastAPI Depends."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        action: str | None = None,
        resource: str | None = None,
        resource_id: str | None = None,
        actor_user_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        ip: str | None = None,
    ) -> None:
        self.page = page
        self.page_size = min(page_size, 100)  # max 100 per api-contract.md §6
        self.action = action
        self.resource = resource
        self.resource_id = resource_id
        self.actor_user_id = actor_user_id
        self.date_from = date_from
        self.date_to = date_to
        self.ip = ip


class AuditEventResponse(AuditEventBase):
    """Response schema for GET /audet and GET /audet/{id} (api-contract.md §6.2)."""

    pass


class AuditEventsPaginatedResponse(BaseModel):
    """Paginated response for GET /audet (api-contract.md §6.1)."""

    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
    pages: int
