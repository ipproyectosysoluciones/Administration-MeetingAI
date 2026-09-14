"""Pydantic request/response models for the users module (api-contract.md §3)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ActiveMembership(BaseModel):
    """The user's membership in the active tenant (nullable ``property_id``)."""

    id: uuid.UUID
    organization_id: uuid.UUID
    property_id: uuid.UUID | None
    role: str
    is_active: bool


class UserMeResponse(BaseModel):
    """Current-user profile + resolved permissions + active membership (§3.1)."""

    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    created_at: datetime
    permissions: list[str]
    tenant_id: uuid.UUID
    tenant_name: str
    active_membership: ActiveMembership


class UserUpdateMeRequest(BaseModel):
    """Self profile update (name/avatar only; restricted fields rejected in the router)."""

    full_name: str | None = None
    avatar_url: str | None = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class UserView(BaseModel):
    """Tenant-scoped user view returned by admin list/get/update (§3.6–3.8)."""

    id: uuid.UUID
    email: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    mfa_enabled: bool
    created_at: datetime
    role: str


class UserListResponse(BaseModel):
    items: list[UserView]
    total: int
    page: int
    page_size: int
    pages: int


class UserAdminUpdateRequest(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None


class UserDeleteResponse(BaseModel):
    message: str
    deleted_at: datetime
