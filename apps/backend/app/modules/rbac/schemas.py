"""RBAC request/response schemas (api-contract.md §5)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# Role-name slug format: lowercase snake_case (base roles share the format).
ROLE_NAME_PATTERN = r"^[a-z][a-z0-9_]{1,99}$"


class PermissionView(BaseModel):
    id: uuid.UUID
    name: str
    resource: str
    action: str
    description: str | None
    is_system: bool


class PermissionListResponse(BaseModel):
    items: list[PermissionView]
    total: int


class RoleView(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    name: str
    display_name: str
    description: str | None
    is_system: bool
    permissions: list[PermissionView]


class RoleListResponse(BaseModel):
    items: list[RoleView]
    total: int


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100, pattern=ROLE_NAME_PATTERN)
    display_name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    permission_ids: list[uuid.UUID] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    permission_ids: list[uuid.UUID] | None = None


class RolePermissionAssignRequest(BaseModel):
    permission_id: uuid.UUID


class UserRoleAssignRequest(BaseModel):
    role_id: uuid.UUID


class UserRoleView(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime


class UserRoleAssignResponse(BaseModel):
    message: str
    user_role: UserRoleView
