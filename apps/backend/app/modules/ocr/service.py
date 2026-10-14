"""OCR service: document text extraction."""

from __future__ import annotations

from typing import BinaryIO

from app.modules.ocr.providers import OCRProvider, OCRResult, TesseractOCRProvider


class OCRService:
    def __init__(self, provider: OCRProvider | None = None) -> None:
        self._provider = provider or TesseractOCRProvider()

    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        """Process a file through OCR and return extracted text with confidence."""
        return await self._provider.process(file_handle, mime_type)
