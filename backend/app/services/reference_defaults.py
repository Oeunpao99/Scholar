"""Canonical Khmer copy for the three applicant categories."""

from __future__ import annotations

CATEGORY_DEFAULTS: list[dict[str, object]] = [
    {
        "code": "current_year",
        "position": 1,
        "roman_numeral": "I.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបឆ្នាំ{year}",
        "description": "Applicants who graduated in the current academic year.",
    },
    {
        "code": "before_current_year",
        "position": 2,
        "roman_numeral": "II.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ{year}",
        "description": "Applicants from previous years.",
    },
    {
        "code": "other_province",
        "position": 3,
        "roman_numeral": "III.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង",
        "description": "Applicants coming from other provinces.",
    },
]

# English fallbacks used by the API when a client cannot render Khmer.
CATEGORY_TITLES_EN: dict[str, str] = {
    "current_year": "Current Year Applicants ({year})",
    "before_current_year": "Before Current Year Applicants ({year})",
    "other_province": "Other Province Applicants",
}

# Khmer keywords that reliably identify a category inside pasted messages.
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "current_year": (
        "ឆ្នាំបច្ចុប្បន្ន",
        "បច្ចុប្បន្ន",
        "ឆ្នាំនេះ",
        "ឆ្នាំ",
        "current year",
    ),
    "before_current_year": (
        "មុនឆ្នាំ",
        "ឆ្នាំមុន",
        "មុនឆ្នាំបច្ចុប្បន្ន",
        "មុន",
        "before current year",
        "previous year",
        "last year",
    ),
    "other_province": (
        "ខេត្តផ្សេង",
        "ខេត្ត",
        "ផ្សេង",
        "other province",
        "other provinces",
        "from other province",
    ),
}
