"""
Knowledge of the scholarship application form ("ពាក្យស្នើសុំអាហារូបករណ៍").

The grade is printed in a box at the top-left of page 1 (e.g. a large "D"),
so unlike the handwritten fields it can be read reliably: find that box and
OCR the single letter inside it.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("scholar.ai.form")

GRADES = "ABCDE"


def _grade_box(gray):
    """(x, y, w, h) of the grade box: a wide rectangle in the page's top-left."""
    import cv2

    h, w = gray.shape[:2]
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    page_area = w * h
    best = None
    for contour in contours:
        approx = cv2.approxPolyDP(contour, 0.03 * cv2.arcLength(contour, True), True)
        if len(approx) != 4:
            continue
        x, y, bw, bh = cv2.boundingRect(approx)
        if y + bh > 0.35 * h or x > 0.45 * w:  # top-left region only
            continue
        if not (0.003 * page_area <= bw * bh <= 0.05 * page_area):
            continue
        if not 1.2 <= bw / bh <= 4.0:  # a landscape box around one letter
            continue
        if best is None or bw * bh > best[2] * best[3]:
            best = (x, y, bw, bh)
    return best


def read_grade_box(page) -> str | None:
    """The printed grade letter (A-E) on the form's first page, or None."""
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image

    try:
        gray = cv2.cvtColor(np.asarray(page.convert("RGB")), cv2.COLOR_RGB2GRAY)
        box = _grade_box(gray)
        if box is None:
            return None
        x, y, bw, bh = box
        inset_x, inset_y = int(bw * 0.12), int(bh * 0.15)  # drop the box border
        cell = gray[y + inset_y : y + bh - inset_y, x + inset_x : x + bw - inset_x]
        text = pytesseract.image_to_string(
            Image.fromarray(cell), lang="eng", config=f"--psm 10 -c tessedit_char_whitelist={GRADES}"
        )
    except Exception:  # best effort: never fail an upload over the grade box
        logger.exception("Grade box reading failed")
        return None
    letters = [c for c in text.upper() if c in GRADES]
    return letters[0] if len(letters) == 1 else None
