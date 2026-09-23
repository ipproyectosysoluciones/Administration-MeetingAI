"""Pydantic schemas for the recordings API (api-contract.md)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RecordingResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    status: str
    duration_seconds: int | None
    uploaded_by: uuid.UUID
    created_at: datetime


class RecordingListResponse(BaseModel):
    items: list[RecordingResponse]
    total: int
    page: int
    page_size: int
    pages: int
