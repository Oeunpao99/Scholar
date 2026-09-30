"""Optional OCR support (screenshots of reports) via pytesseract."""

from __future__ import annotations

import base64
import binascii
import io
import logging

from app.core.config import settings
from app.core.errors import ValidationError

logger = logging.getLogger("scholar.ai.ocr")


class OcrService:
    """Thin wrapper so the rest of the app never imports pytesseract directly."""

    def __init__(self) -> None:
        if settings.TESSERACT_CMD:
            import os

            os.environ.setdefault("TESSERACT_CMD", settings.TESSERACT_CMD)

    @property
    def available(self) -> bool:
        if not settings.OCR_ENABLED:
            return False
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            return False
        return self._tesseract_binary_ok()

    def extract_text(self, images: list[str]) -> str:
        if not images:
            return ""
        if not self.available:
            raise ValidationError(
                "OCR is not available on this server. Paste the text instead, "
                "or enable the OCR_ENABLED setting and install tesseract."
            )
        import pytesseract
        from PIL import Image

        chunks: list[str] = []
        for payload in images:
            image = Image.open(io.BytesIO(self._decode(payload)))
            text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGES)
            if text.strip():
                chunks.append(text.strip())
        return "\n".join(chunks)

    @staticmethod
    def _decode(payload: str) -> bytes:
        raw = payload.strip()
        if raw.startswith("data:"):
            raw = raw.split(",", 1)[1] if "," in raw else raw
        try:
            return base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValidationError("One of the uploaded images is not valid base64.") from exc

    @staticmethod
    def _tesseract_binary_ok() -> bool:
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
        except Exception:  # pragma: no cover - depends on host install
            return False
        return True
