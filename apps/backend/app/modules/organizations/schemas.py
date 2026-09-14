"""Pydantic request/response models for the organizations module (api-contract.md §4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


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
