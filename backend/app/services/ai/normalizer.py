"""Text normalisation helpers for Khmer/English mixed input."""

from __future__ import annotations

import re
import unicodedata

from app.services.ai.patterns import KHMER_MONTHS, ORDINAL_MARKS

# Khmer digits ០-៩ -> ASCII 0-9
KHMER_DIGITS = {
    "០": "0", "១": "1", "២": "2", "៣": "3", "៤": "4",
    "៥": "5", "៦": "6", "៧": "7", "៨": "8", "៩": "9",
    "០": "0", "១": "1", "២": "2",
    # Thai digits occasionally appear in OCR output.
    "๐": "0", "๑": "1", "๒": "2", "๓": "3", "๔": "4",
    "๕": "5", "๖": "6", "๗": "7", "๘": "8", "๙": "9",
}

_ZERO_WIDTH = dict.fromkeys(map(ord, "‌‍﻿"), None)
_MULTISPACE = re.compile(r"[ \t ]+")


def khmer_to_ascii_digits(text: str) -> str:
    return "".join(KHMER_DIGITS.get(ch, ch) for ch in text)


def normalize_for_parsing(text: str) -> str:
    """
    Produce a parsing-friendly variant of the raw text:
      * NFKC normalisation (collapses full-width digits and Latin look-alikes)
      * Khmer/Thai digits converted to ASCII
      * zero-width characters removed, spaces collapsed
    """
    if not text:
        return ""
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.translate(_ZERO_WIDTH)
    cleaned = khmer_to_ascii_digits(cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _MULTISPACE.sub(" ", cleaned)
    return cleaned.strip()


def normalize_key(text: str) -> str:
    """Aggressive normalisation for keyword matching."""
    return normalize_for_parsing(text).lower()


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in normalize_for_parsing(text).split("\n") if line.strip()]


def to_int(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    digits = re.sub(r"[^\d-]", "", khmer_to_ascii_digits(str(value)))
    if not digits or digits == "-":
        return 0
    try:
        return int(digits)
    except ValueError:
        return 0


def strip_ordinal_marks(text: str) -> str:
    """Remove Khmer/Lao ordinal marks so month names can be looked up."""
    return "".join(ch for ch in text if ch not in set(ORDINAL_MARKS))
