"""Pydantic request/response models for meetings (meetings-crud change)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MeetingCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    location: str | None = Field(default=None, max_length=255)
    modality: str = Field(default="in_person", pattern="^(in_person|virtual|hybrid)$")


class MeetingUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    modality: str | None = Field(default=None, pattern="^(in_person|virtual|hybrid)$")
    status: str | None = Field(default=None, pattern="^(scheduled|in_progress|finished|cancelled)$")


class MeetingResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime
    location: str | None
    modality: str
    status: str
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    items: list[MeetingResponse]
    total: int
    page: int
    page_size: int
    pages: int


class ParticipantAddRequest(BaseModel):
    """Exactly one channel: ``user_id`` (internal) or ``external_email``."""

    user_id: uuid.UUID | None = None
    external_email: str | None = Field(default=None, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: str = Field(default="attendee", pattern="^(organizer|presenter|attendee)$")


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: uuid.UUID | None
    external_email: str | None
    role: str
    created_at: datetime


class ParticipantListResponse(BaseModel):
    items: list[ParticipantResponse]
    total: int
