"""Documents module."""

from app.modules.documents.models import (
    Document,
    DocumentStatus,
    DocumentType,
    DocumentVersion,
    OcrStatus,
)
from app.modules.documents.router import router as documents_router
from app.modules.documents.service import DocumentService

__all__ = [
    "Document",
    "DocumentStatus",
    "DocumentType",
    "DocumentVersion",
    "OcrStatus",
    "DocumentService",
    "documents_router",
]