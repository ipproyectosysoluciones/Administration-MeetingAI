"""Pydantic request/response models for the organizations module (api-contract.md §4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# -- organization ------------------------------------------------------------


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    settings: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100)
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    settings: dict[str, Any] | None = None


# -- property/group ----------------------------------------------------------


class PropertyResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    code: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class PropertyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None


class PropertyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None


class PropertyListResponse(BaseModel):
    items: list[PropertyResponse]
    total: int
    page: int
    page_size: int
    pages: int


# -- membership --------------------------------------------------------------


class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    property_id: uuid.UUID | None
    role: str
    is_active: bool
    user_email: str | None
    user_full_name: str | None
    created_at: datetime


class MembershipCreateRequest(BaseModel):
    user_id: uuid.UUID
    role: str = Field(min_length=1, max_length=100)
    property_id: uuid.UUID | None = None


class MembershipUpdateRequest(BaseModel):
    role: str | None = Field(default=None, min_length=1, max_length=100)
    property_id: uuid.UUID | None = None


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int
    page: int
    page_size: int
    pages: int
