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
        import sys
        from pathlib import Path

        cmd = settings.TESSERACT_CMD
        if not cmd and sys.platform == "win32":
            for default_path in [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]:
                if Path(default_path).is_file():
                    cmd = default_path
                    break

        if cmd:
            try:
                import pytesseract
            except ImportError:
                return
            pytesseract.pytesseract.tesseract_cmd = str(cmd)

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
        from PIL import Image

        return self.extract_text_from_images(
            [Image.open(io.BytesIO(self._decode(payload))) for payload in images]
        )

    def extract_text_from_images(self, images: list, psm: int | None = None) -> str:
        """OCR already-decoded PIL images, one text block per image."""
        if not images:
            return ""
        if not self.available:
            raise ValidationError(
                "OCR is not available on this server. Enable the OCR_ENABLED setting and install tesseract."
            )
        import pytesseract

        missing = self.missing_languages()
        if missing:
            raise ValidationError(
                f"OCR language pack missing on this server: {', '.join(missing)} "
                f"(add {missing[0]}.traineddata to Tesseract's tessdata folder)."
            )

        config_parts = ["--oem 1", "--dpi 300"]
        if psm is not None:
            config_parts.append(f"--psm {psm}")
        config = " ".join(config_parts)

        chunks: list[str] = []
        for image in images:
            text = pytesseract.image_to_string(
                _prepare(image), lang=settings.OCR_LANGUAGES, config=config
            )
            if text.strip():
                chunks.append(text.strip())
        return "\n".join(chunks)

    def missing_languages(self) -> list[str]:
        """Configured OCR languages (e.g. "khm+eng") that Tesseract doesn't have."""
        import pytesseract

        try:
            installed = set(pytesseract.get_languages(config=""))
        except Exception:  # pragma: no cover - depends on host install
            return []
        return [lang for lang in settings.OCR_LANGUAGES.split("+") if lang not in installed]

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


def _deskew(gray):
    """Detect and correct small rotational skews (-15 to +15 deg)."""
    import cv2
    import numpy as np

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 150:
        return gray

    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5 or abs(angle) > 15.0:
        return gray

    h, w = gray.shape[:2]
    center = (w // 2, h // 2)
    mat = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        gray, mat, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=255
    )


def _flatten_lighting(gray):
    """Attenuate paper shadows, phone camera gradients, and uneven lighting."""
    import cv2

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 35))
    dilated = cv2.morphologyEx(gray, cv2.MORPH_DILATE, kernel)
    bg = cv2.medianBlur(dilated, 21)
    diff = 255 - cv2.absdiff(gray, bg)
    return cv2.normalize(diff, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8UC1)


def _prepare(image):
    """
    Grayscale, deskew, normalize non-uniform lighting, and upscale.
    Khmer stacked vowels and sub-consonants (ជើង) require sharp, high-contrast,
    at least ~35px+ glyphs without shadow artifacts.
    """
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    image = ImageOps.exif_transpose(image).convert("L")
    gray = np.asarray(image)

    # 1. Deskew
    try:
        gray = _deskew(gray)
    except Exception:
        logger.debug("Deskew skipped", exc_info=True)

    # 2. Flatten uneven lighting / shadow removal
    try:
        gray = _flatten_lighting(gray)
    except Exception:
        logger.debug("Lighting flattening skipped", exc_info=True)

    # 3. Local contrast enhancement with CLAHE
    try:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    except Exception:
        pass

    # 4. Upscale small images so Khmer glyphs have adequate height
    h, w = gray.shape[:2]
    if w < 1800:
        scale = 1800 / w
        gray = cv2.resize(gray, (1800, round(h * scale)), interpolation=cv2.INTER_CUBIC)

    return Image.fromarray(gray)
