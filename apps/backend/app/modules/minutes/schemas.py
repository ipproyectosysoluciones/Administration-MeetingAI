"""Pydantic schemas for the minutes API (meetings-minutes / MIN-103)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MinuteCreateRequest(BaseModel):
    title: str = Field(max_length=200)
    content: str = ""
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_request_id: str | None = None


class MinuteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    meeting_id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    content: str
    version: int
    status: str
    created_by: uuid.UUID
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    published_by: uuid.UUID | None
    published_at: datetime | None
    archived_at: datetime | None
    ai_provider: str | None
    ai_model: str | None
    ai_request_id: str | None
    created_at: datetime
    updated_at: datetime


class MinuteListResponse(BaseModel):
    items: list[MinuteResponse]
    total: int
    page: int
    page_size: int
    pages: int
