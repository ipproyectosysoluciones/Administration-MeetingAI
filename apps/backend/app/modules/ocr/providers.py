"""OCR provider abstraction: the domain port plus the real Tesseract/OCRmyPDF adapter.

PRD §16 interface (verbatim): ``OCRProvider ├── process() ├── extract_text() └── confidence()``
with initial implementations *"Tesseract. OCRmyPDF."*. The domain never imports
pytesseract/ocrmypdf/PIL SDKs directly (AGENTS.md rules 11-12): only this adapter
does, and lazily, so test/CI environments work without the heavy ``ocr`` extra
installed (precedent: FasterWhisperProvider). Engines are injectable for tests.
"""

from __future__ import annotations

import io
import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

ImageEngine = Callable[[bytes, str], "tuple[str, float]"]
PdfEngine = Callable[[bytes], "tuple[str, float, int]"]

# PRD §16 allowlist mimes; jpg/jpeg both map to image/jpeg (documents schemas).
_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/tiff"})


class OCRError(Exception):
    """Base OCR domain error (OCR-4 pipeline catches this family)."""


class PermanentOCRError(OCRError):
    """OCR failure that will not succeed on retry (bad input, corrupt data)."""


@dataclass
class OCRResult:
    text: str
    confidence: float
    pages: int


class OCRProvider(ABC):
    """Abstract OCR provider (PRD §16)."""

    @abstractmethod
    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        """Process a file and return OCR result."""
        ...

    async def extract_text(self, file_handle: BinaryIO, mime_type: str) -> str:
        """PRD §16 ``extract_text()``: normalized text of the processed file."""
        return (await self.process(file_handle, mime_type)).text

    async def confidence(self, file_handle: BinaryIO, mime_type: str) -> float:
        """PRD §16 ``confidence()``: OCR confidence of the processed file."""
        return (await self.process(file_handle, mime_type)).confidence


def _default_image_engine(data: bytes, language: str) -> tuple[str, float]:
    """pytesseract for images: text via image_to_string, confidence as the mean
    of per-word image_to_data confidences (words with conf < 0 are skipped)."""
    import pytesseract  # type: ignore  # noqa: PLC0415
    from PIL import Image  # type: ignore  # noqa: PLC0415

    img = Image.open(io.BytesIO(data))
    text = str(pytesseract.image_to_string(img, lang=language))
    output = pytesseract.image_to_data(img, lang=language, output_type=pytesseract.Output.DICT)
    confs = []
    for conf in output.get("conf", []):
        try:
            value = float(conf)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            confs.append(value)
    confidence = sum(confs) / len(confs) if confs else 0.0
    return text, confidence


def _default_pdf_engine(data: bytes) -> tuple[str, float, int]:
    """ocrmypdf for PDFs (SDD design.md): sidecar text; page count from the
    sidecar's form-feed separators; confidence as the fraction of pages that
    produced text (documented simple proxy — per-page OCR confidence for PDFs
    would require page rendering, out of OCR-3 scope).

    Consumer contract (OCR-4): this confidence feeds the quality gate
    (`OCR_CONFIDENCE_THRESHOLD`, SDD default 0.60). A PDF whose pages all
    yield text scores 1.0; an unreadable scan scores 0.0 and the gate flags
    it `LOW_CONFIDENCE` for human correction — page-level OCR confidence
    aggregation is a documented follow-up if the proxy proves too coarse.
    """
    import ocrmypdf  # type: ignore  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "in.pdf"
        out_path = Path(tmp) / "out.pdf"
        sidecar_path = Path(tmp) / "sidecar.txt"
        in_path.write_bytes(data)
        ocrmypdf.ocr(str(in_path), str(out_path), sidecar=str(sidecar_path))
        text = sidecar_path.read_text(encoding="utf-8", errors="replace")
    page_texts = text.split("\f")
    pages = max(len(page_texts), 1)
    pages_with_text = sum(1 for page in page_texts if page.strip())
    confidence = pages_with_text / pages
    return text, confidence, pages


class TesseractOCRProvider(OCRProvider):
    """Real OCR provider per PRD §16 / SDD design.md.

    Images (jpg/jpeg/png/tiff) run through pytesseract; PDFs through OCRmyPDF
    (sidecar text). Dispatch is by declared mime type. Engines are injectable
    for tests; without injection the heavy imports happen lazily inside the
    default engines and raise a typed error if the ``ocr`` extra is missing.
    """

    def __init__(
        self,
        image_engine: ImageEngine | None = None,
        pdf_engine: PdfEngine | None = None,
        language: str | None = None,
    ) -> None:
        self._image_engine = image_engine
        self._pdf_engine = pdf_engine
        self.language = language or os.environ.get("OCR_LANGUAGE", "spa")

    async def process(self, file_handle: BinaryIO, mime_type: str) -> OCRResult:
        data = file_handle.read()
        try:
            if mime_type == "application/pdf":
                pdf_engine = self._pdf_engine or _default_pdf_engine
                text, confidence, pages = pdf_engine(data)
            elif mime_type in _IMAGE_MIMES:
                image_engine = self._image_engine or _default_image_engine
                text, confidence = image_engine(data, self.language)
                pages = 1
            else:
                raise PermanentOCRError(f"UNSUPPORTED_OCR_MIME: {mime_type}")
        except PermanentOCRError:
            raise
        except Exception as exc:
            raise PermanentOCRError(f"OCR_FAILED ({mime_type}): {exc}") from exc
        return OCRResult(text=text, confidence=confidence, pages=pages)
