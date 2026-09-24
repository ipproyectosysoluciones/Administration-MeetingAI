"""Pydantic schemas for the transcription API (api-contract.md)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None


class TranscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recording_id: uuid.UUID
    meeting_id: uuid.UUID
    tenant_id: uuid.UUID
    language: str | None
    text: str
    segments: list[dict[str, Any]]
    avg_confidence: Decimal | None
    model_used: str | None
    version: int
    status: str
    error: str | None
    created_at: datetime
    updated_at: datetime


class TranscriptionListResponse(BaseModel):
    items: list[TranscriptionResponse]
    total: int
    page: int
    page_size: int
    pages: int
