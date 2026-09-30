"""Student photo cropping and normalisation.

The Haar face detector itself needs a real face to test; these cover the
geometry around it (framing, snapping to the printed photo box) with
synthetic pages and a supplied face position.
"""

from __future__ import annotations

import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from app.core.errors import ValidationError
from app.services.ai import photo as photo_mod
from app.services.ai.photo import (
    extract_student_photo,
    frame_from_face,
    normalize_uploaded_photo,
    snap_to_frame,
)


def _gray(image: Image.Image):
    return np.asarray(image.convert("L"))


def test_frame_from_face_is_a_3_by_4_portrait_around_the_face():
    x, y, w, h = frame_from_face((400, 300, 110, 110), 2000, 3000)
    assert abs(h / w - 4 / 3) < 0.02
    assert x < 400 and x + w > 510  # face horizontally inside
    assert y < 300 < y + h  # room above the face for hair
    assert abs((x + w / 2) - 455) <= 1  # centred on the face


def test_frame_from_face_is_clamped_to_the_page():
    x, y, w, h = frame_from_face((5, 5, 100, 100), 300, 300)
    assert x >= 0 and y >= 0 and x + w <= 300 and y + h <= 300


def test_snaps_to_the_printed_photo_box_around_the_face():
    page = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((900, 100, 1140, 420), outline="black", width=4)  # 3x4 photo box
    draw.rectangle((60, 700, 1140, 760), outline="black", width=2)  # unrelated table line
    box = snap_to_frame(_gray(page), (960, 170, 120, 120))
    assert box is not None
    x, y, w, h = box
    assert 900 <= x <= 912 and 100 <= y <= 112
    assert 1128 <= x + w <= 1140 and 408 <= y + h <= 420


def test_a_form_section_around_the_photo_is_not_mistaken_for_the_photo_box():
    # Photo sits in the top-right of a bigger header box (as on real forms);
    # only the tight photo box may be chosen - never the header section.
    page = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(page)
    draw.rectangle((40, 40, 1160, 900), outline="black", width=4)  # form section
    draw.rectangle((900, 100, 1140, 420), outline="black", width=4)  # photo box
    x, y, w, h = snap_to_frame(_gray(page), (960, 170, 120, 120))
    assert x >= 900 and x + w <= 1140 and y + h <= 420


def test_oversized_box_alone_falls_back_to_face_framing():
    page = Image.new("RGB", (1200, 1600), "white")
    ImageDraw.Draw(page).rectangle((600, 60, 1160, 800), outline="black", width=4)
    assert snap_to_frame(_gray(page), (960, 170, 120, 120)) is None


def test_no_frame_when_the_face_is_not_inside_a_box():
    page = Image.new("RGB", (1200, 1600), "white")
    ImageDraw.Draw(page).rectangle((100, 900, 340, 1220), outline="black", width=4)
    assert snap_to_frame(_gray(page), (960, 170, 120, 120)) is None


def test_extracts_a_bounded_jpeg_crop_when_a_face_is_found(monkeypatch):
    page = Image.new("RGB", (1200, 1600), "white")
    ImageDraw.Draw(page).rectangle((900, 100, 1140, 420), outline="black", width=4)
    monkeypatch.setattr(photo_mod, "_faces", lambda gray: [(960, 170, 120, 120)])
    monkeypatch.setattr(photo_mod, "skin_ratio", lambda rgb, face: 0.8)
    data = extract_student_photo([page])
    assert data is not None and data[:3] == b"\xff\xd8\xff"  # JPEG
    crop = Image.open(io.BytesIO(data))
    assert crop.width <= 360 and crop.height <= 480
    assert abs(crop.height / crop.width - 4 / 3) < 0.1


def test_blank_page_has_no_photo():
    assert extract_student_photo([Image.new("RGB", (1200, 1600), "white")]) is None


def test_detection_errors_never_fail_the_upload(monkeypatch):
    def boom(gray):
        raise RuntimeError("opencv exploded")

    monkeypatch.setattr(photo_mod, "_faces", boom)
    assert extract_student_photo([Image.new("RGB", (100, 100), "white")]) is None


def test_uploaded_photo_is_resized_to_jpeg():
    buf = io.BytesIO()
    Image.new("RGBA", (3000, 4000), (200, 100, 50, 255)).save(buf, format="PNG")
    out = Image.open(io.BytesIO(normalize_uploaded_photo(buf.getvalue())))
    assert out.format == "JPEG"
    assert out.width <= 720 and out.height <= 960


@pytest.mark.parametrize("data", [b"", b"not an image", b"%PDF-1.7 nope"])
def test_uploaded_photo_rejects_non_images(data):
    with pytest.raises(ValidationError):
        normalize_uploaded_photo(data)
