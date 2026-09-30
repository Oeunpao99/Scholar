"""
Student photos: find the ID photo on a scanned application form, and
normalise photos uploaded by hand.

Detection: OpenCV's frontal-face Haar cascade finds the largest face on the
page. If the face sits inside a printed photo frame (a rectangle a few times
the face's size), crop to that frame; otherwise frame the face the way an
ID photo is framed (3:4, head and shoulders).
"""

from __future__ import annotations

import io
import logging
from functools import lru_cache

from app.core.errors import ValidationError

logger = logging.getLogger("scholar.ai.photo")

Box = tuple[int, int, int, int]  # x, y, width, height

MAX_PHOTO_SIZE = (360, 480)  # stored size, 3:4 portrait
MAX_UPLOAD_SIZE = (720, 960)  # hand-uploaded photos keep a little more detail
DETECT_MAX_SIDE = 1600  # downscale big scans before detecting (speed)
JPEG_QUALITY = 85


@lru_cache(maxsize=1)
def _cascade():
    import cv2

    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():  # pragma: no cover - broken install
        raise RuntimeError(f"Could not load face cascade from {path}")
    return cascade


def _faces(gray) -> list[Box]:
    """Faces on a grayscale page, in full-page coordinates."""
    import cv2

    h, w = gray.shape[:2]
    scale = min(1.0, DETECT_MAX_SIDE / max(w, h))
    small = cv2.resize(gray, None, fx=scale, fy=scale) if scale < 1 else gray
    # An ID photo on an A4 form is ~15% of the page width; its face ~8%.
    # Ignoring anything much smaller cuts false hits on text and stamps.
    min_side = max(40, int(0.04 * small.shape[1]))
    found = _cascade().detectMultiScale(
        small, scaleFactor=1.1, minNeighbors=6, minSize=(min_side, min_side)
    )
    return [tuple(int(v / scale) for v in f) for f in found]  # type: ignore[misc]


def frame_from_face(face: Box, page_w: int, page_h: int) -> Box:
    """ID-photo framing around a face: face ~55% of width, 3:4, room for hair."""
    x, y, w, h = face
    pw = w / 0.55
    ph = pw * 4 / 3
    left = x + w / 2 - pw / 2
    top = y - 0.45 * h
    return _clamp((round(left), round(top), round(pw), round(ph)), page_w, page_h)


def snap_to_frame(gray, face: Box) -> Box | None:
    """The printed photo frame around ``face``, if the form has one."""
    import cv2

    fx, fy, fw, fh = face
    face_area = fw * fh
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    best: Box | None = None
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        inside = x <= fx and y <= fy and x + w >= fx + fw and y + h >= fy + fh
        # An ID photo is head and shoulders: the face fills a good share of
        # it (area 1.5-6x the face, face >= 35% of its width). Anything
        # looser is a form section or the page border, not the photo.
        if not inside or not (1.5 * face_area <= w * h <= 6 * face_area):
            continue
        if fw < 0.35 * w or not 0.55 <= w / h <= 1.0:  # portrait-ish photo box
            continue
        if best is None or w * h < best[2] * best[3]:
            best = (x, y, w, h)
    if best is None:
        return None
    x, y, w, h = best
    inset = max(2, round(min(w, h) * 0.02))  # drop the frame line itself
    return (x + inset, y + inset, w - 2 * inset, h - 2 * inset)


def _clamp(box: Box, page_w: int, page_h: int) -> Box:
    x, y, w, h = box
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(page_w, x + w), min(page_h, y + h)
    return (x0, y0, max(1, x1 - x0), max(1, y1 - y0))


def _to_jpeg(image, max_size: tuple[int, int]) -> bytes:
    image = image.convert("RGB")
    image.thumbnail(max_size)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


MIN_SKIN_RATIO = 0.15  # share of skin-toned pixels a real face must have


def skin_ratio(rgb, box: Box) -> float:
    """Share of skin-toned pixels in the middle of ``box`` (YCrCb skin range).

    The Haar cascade also fires on handwriting and printed text; paper and
    ink have almost no skin-toned pixels, a real face photo has plenty.
    """
    import cv2

    x, y, w, h = box
    core = rgb[y + h // 4 : y + 3 * h // 4, x + w // 4 : x + 3 * w // 4]  # cheeks/nose
    if core.size == 0:
        return 0.0
    ycrcb = cv2.cvtColor(core, cv2.COLOR_RGB2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    return float((mask > 0).mean())


def _candidates(image) -> list[tuple[float, Box]]:
    """(skin score, photo box) for each plausible face on one page."""
    import cv2
    import numpy as np

    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    out = []
    for face in _faces(gray):
        score = skin_ratio(rgb, face)
        if score >= MIN_SKIN_RATIO:
            box = snap_to_frame(gray, face) or frame_from_face(face, image.width, image.height)
            out.append((score, box))
    return out


def find_photo_box(image) -> Box | None:
    """Where the student's photo is on one page image, or None."""
    found = _candidates(image)
    return max(found, key=lambda c: c[0])[1] if found else None


def extract_student_photo(pages: list) -> bytes | None:
    """JPEG of the most face-like photo across all pages.

    Compare every page instead of taking the first hit: a form page can
    produce a weak false detection while the real ID photo sits on a
    later page.
    """
    best: tuple[float, int, Box] | None = None
    try:
        for index, page in enumerate(pages):
            for score, box in _candidates(page):
                if best is None or score > best[0]:
                    best = (score, index, box)
    except Exception:  # detection is best-effort; never fail the upload
        logger.exception("Photo detection failed")
        return None
    if best is None:
        return None
    _, index, (x, y, w, h) = best
    return _to_jpeg(pages[index].crop((x, y, x + w, y + h)), MAX_PHOTO_SIZE)


def normalize_uploaded_photo(data: bytes) -> bytes:
    """Validate a hand-uploaded photo and store it as a bounded-size JPEG."""
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not data:
        raise ValidationError("The uploaded photo is empty.")
    Image.MAX_IMAGE_PIXELS = 40_000_000
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
        raise ValidationError("Upload the photo as JPG, PNG or WebP.") from exc
    return _to_jpeg(ImageOps.exif_transpose(image), MAX_UPLOAD_SIZE)
