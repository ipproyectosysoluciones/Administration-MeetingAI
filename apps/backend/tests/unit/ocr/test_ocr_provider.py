"""OCR-300: real OCRProvider port + TesseractOCRProvider (PRD §16, SDD design.md)."""

from __future__ import annotations

import io
from typing import BinaryIO

import pytest

from app.modules.ocr.providers import (
    OCRProvider,
    OCRResult,
    PermanentOCRError,
    TesseractOCRProvider,
)


class FakeProvider(OCRProvider):
    """Deterministic fake satisfying the port (SDD test-plan: provider fakes)."""

    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        return OCRResult(text="fake text", confidence=0.75, pages=2)


def _handle(data: bytes = b"data") -> BinaryIO:
    return io.BytesIO(data)


async def test_fake_provider_satisfies_port() -> None:
    provider = FakeProvider()
    result = await provider.process(_handle(), "image/png")
    assert result == OCRResult(text="fake text", confidence=0.75, pages=2)
    # PRD §16 interface: extract_text() and confidence() compose over process().
    assert await provider.extract_text(_handle(), "image/png") == "fake text"
    assert await provider.confidence(_handle(), "image/png") == 0.75


async def test_image_path_uses_injected_engine() -> None:
    calls: list[tuple[bytes, str]] = []

    def image_engine(data: bytes, lang: str) -> tuple[str, float]:
        calls.append((data, lang))
        return "texto de imagen", 0.88

    provider = TesseractOCRProvider(image_engine=image_engine)
    result = await provider.process(_handle(b"imgbytes"), "image/png")
    assert result.text == "texto de imagen"
    assert result.confidence == 0.88
    assert result.pages == 1
    assert calls == [(b"imgbytes", provider.language)]


async def test_pdf_path_uses_injected_engine() -> None:
    def pdf_engine(data: bytes) -> tuple[str, float, int]:
        assert data == b"%PDF-fake"
        return "texto pdf", 0.5, 3

    provider = TesseractOCRProvider(pdf_engine=pdf_engine)
    result = await provider.process(_handle(b"%PDF-fake"), "application/pdf")
    assert result == OCRResult(text="texto pdf", confidence=0.5, pages=3)


async def test_mime_dispatch_routes_each_format() -> None:
    image_calls: list[str] = []
    pdf_calls: list[str] = []

    def image_engine(data: bytes, lang: str) -> tuple[str, float]:
        image_calls.append("img")
        return "t", 0.9

    def pdf_engine(data: bytes) -> tuple[str, float, int]:
        pdf_calls.append("pdf")
        return "t", 0.9, 1

    provider = TesseractOCRProvider(image_engine=image_engine, pdf_engine=pdf_engine)
    for mime in ("image/jpeg", "image/png", "image/tiff"):
        await provider.process(_handle(), mime)
    await provider.process(_handle(), "application/pdf")
    assert len(image_calls) == 3
    assert len(pdf_calls) == 1


async def test_unsupported_mime_raises_permanent() -> None:
    provider = TesseractOCRProvider(image_engine=lambda d, lang: ("t", 1.0))
    with pytest.raises(PermanentOCRError, match="UNSUPPORTED_OCR_MIME"):
        await provider.process(_handle(), "text/plain")


async def test_engine_failure_maps_to_permanent_error() -> None:
    def broken_engine(data: bytes, lang: str) -> tuple[str, float]:
        raise ValueError("corrupt image data")

    provider = TesseractOCRProvider(image_engine=broken_engine)
    with pytest.raises(PermanentOCRError):
        await provider.process(_handle(), "image/png")


async def test_extract_text_and_confidence_wrappers() -> None:
    provider = TesseractOCRProvider(image_engine=lambda d, lang: ("hola", 0.42))
    assert await provider.extract_text(_handle(), "image/jpeg") == "hola"
    assert await provider.confidence(_handle(), "image/jpeg") == 0.42
