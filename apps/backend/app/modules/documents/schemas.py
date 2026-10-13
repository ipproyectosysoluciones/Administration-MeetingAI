"""Pydantic request/response models for the documents module."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

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
    description: Optional[str] = None
    type: DocumentType
    meeting_id: Optional[uuid.UUID] = None


class DocumentCreateRequest(DocumentBase):
    pass


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    meeting_id: Optional[uuid.UUID] = None


class DocumentVersionCreateRequest(BaseModel):
    file_path: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(..., gt=0)
    sha256: str = Field(..., min_length=64, max_length=64)
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = Field(None, ge=0, le=1)
    ocr_status: Optional[str] = None
    pages: Optional[int] = None
    metadata_json: dict = {}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    meeting_id: Optional[uuid.UUID]
    title: str
    description: Optional[str]
    type: DocumentType
    status: str
    file_path: str
    file_size: int
    sha256: str
    mime_type: str
    version: int
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    ocr_status: str
    ocr_error: Optional[str]
    pages: Optional[int]
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
    ocr_text: Optional[str]
    ocr_confidence: Optional[float]
    ocr_status: str
    pages: Optional[int]
    metadata_json: dict
    created_by: Optional[uuid.UUID]
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentVersionListResponse(BaseModel):
    items: list[DocumentVersionResponse]
    total: int
    page: int
    page_size: int
    pages: int