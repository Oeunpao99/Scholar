"""Turn an uploaded scan (image or PDF) into page images for OCR and photo search."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from app.core.errors import ValidationError

TEXT_PAGES = 2  # the application form itself is page 1 (page 2 as a fallback)
PHOTO_PAGES = 8  # the ID photo is usually attached a few pages later
TEXT_DPI, TEXT_MAX_SIDE = 300, 3600  # ~300 dpi is what Tesseract reads Khmer best at
PHOTO_DPI, PHOTO_MAX_SIDE = 200, 2400
MAX_PIXELS = 40_000_000  # refuse decompression bombs


@dataclass(slots=True)
class LoadedDocument:
    text_pages: list = field(default_factory=list)  # high resolution, for OCR
    photo_pages: list = field(default_factory=list)  # medium resolution, for the photo
    page_count: int = 0


def load_document(data: bytes) -> LoadedDocument:
    """Decode by content, not by file name: PDF -> rendered pages, else one image."""
    if not data:
        raise ValidationError("The uploaded file is empty.")
    if data.lstrip()[:5] == b"%PDF-":
        return _pdf(data)
    image = _image(data)
    return LoadedDocument(text_pages=[image], photo_pages=[image], page_count=1)


def _image(data: bytes):
    from PIL import Image, ImageOps, UnidentifiedImageError

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValidationError("Upload a JPG, PNG, WebP or PDF file.") from exc
    return ImageOps.exif_transpose(image)  # phone photos are often stored sideways


def _render(page, dpi: int, max_side: int):
    # Cap by pixel size too: some scans have huge page sizes (e.g. 2675x3878 pt),
    # where a plain dpi scale would allocate hundreds of megapixels.
    width, height = page.get_size()
    scale = min(dpi / 72, max_side / max(width, height))
    return page.render(scale=scale).to_pil()


def _pdf(data: bytes) -> LoadedDocument:
    import pypdfium2 as pdfium

    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise ValidationError("The PDF could not be opened (damaged or password-protected).") from exc
    try:
        count = len(pdf)
        return LoadedDocument(
            text_pages=[_render(pdf[i], TEXT_DPI, TEXT_MAX_SIDE) for i in range(min(count, TEXT_PAGES))],
            photo_pages=[_render(pdf[i], PHOTO_DPI, PHOTO_MAX_SIDE) for i in range(min(count, PHOTO_PAGES))],
            page_count=count,
        )
    finally:
        pdf.close()
