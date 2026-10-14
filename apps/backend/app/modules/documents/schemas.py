"""Pydantic request/response models for the documents module."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PDF = "pdf"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OcrStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: DocumentType
    meeting_id: uuid.UUID | None = None


class DocumentCreateRequest(DocumentBase):
    pass


class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    meeting_id: uuid.UUID | None = None


class DocumentVersionCreateRequest(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    ocr_text: str | None = None
    ocr_confidence: float | None = Field(None, ge=0, le=1)
    ocr_status: str | None = None
    pages: int | None = None
    metadata_json: dict = {}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: uuid.UUID | None
    title: str
    description: str | None
    type: DocumentType
    status: str
    file_path: str
    file_size: int
    sha256: str
    mime_type: str
    version: int
    ocr_text: str | None
    ocr_confidence: float | None
    ocr_status: str
    ocr_error: str | None
    pages: int | None
    uploaded_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version: int
    file_path: str
    file_size: int
    sha256: str
    ocr_text: str | None
    ocr_confidence: float | None
    ocr_status: str
    pages: int | None
    metadata_json: dict
    created_by: uuid.UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]
    total: int
    page: int
    page_size: int
    pages: int