"""OCR provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int


class OCRProvider(ABC):
    """Abstract OCR provider."""

    @abstractmethod
    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        """Process a file and return OCR result."""
        ...


class TesseractOCRProvider(OCRProvider):
    """Tesseract OCR provider (mock implementation for testing)."""

    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        # Mock implementation - in production would use pytesseract or similar
        content = file_handle.read()
        return OCRResult(
            text=f"OCR extracted text from {len(content)} bytes",
            confidence=0.95,
            pages=1,
        )


class OCRmyPDFProvider(OCRProvider):
    """OCRmyPDF provider (mock implementation for testing)."""

    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        # Mock implementation - in production would use OCRmyPDF
        content = file_handle.read()
        return OCRResult(
            text=f"OCRmyPDF extracted text from {len(content)} bytes",
            confidence=0.92,
            pages=1,
        )
