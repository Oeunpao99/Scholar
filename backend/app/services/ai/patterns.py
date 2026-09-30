"""Regular expressions used by the built-in extraction parser.

The patterns accept both the canonical Khmer Telegram layout and the loose
English phrasing staff use on Facebook, WhatsApp and scanned documents.

Khmer literals below are copied verbatim from the ministry template so the
parser can never drift from the report it has to understand.
"""

from __future__ import annotations

import re

# Khmer/Lao marks that follow ordinal day numbers (e.g. "កុម្ភៈ១០").
ORDINAL_MARKS = "\u17b4\u17b5\u17b6\u17b7\u17b8\u17b9\u17ba\u17bb\u17bc\u17bd\u17be\u17bf\u17c0\u17c1\u17c2\u17c3"

# Khmer and English month names -> month number.
KHMER_MONTHS: dict[str, int] = {
    "មករា": 1, "កុម្ភៈ": 2, "មីនា": 3, "មេសា": 4, "ឧសភា": 5, "មិថុនា": 6,
    "កក្កដា": 7, "សីហា": 8, "កញ្ញា": 9, "តុលា": 10, "វិច្ឆិកា": 11, "ធ្នូ": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

# --------------------------------------------------------------------- dates
DATE_DMY = re.compile(r"\b(\d{1,2})\s*[/\-.]+\s*(\d{1,2})\s*[/\-.]+\s*(\d{2,4})\b")
DATE_YMD = re.compile(r"\b(\d{4})\s*[/\-.]+\s*(\d{1,2})\s*[/\-.]+\s*(\d{1,2})\b")
DATE_MONTH_NAME = re.compile(rf"\b(\d{{1,2}})\s*([A-Za-z\u1780-\u17ff]{{3,12}})\s*(\d{{4}})\b")
# Long Khmer form: "\u1790\u17d2\u1784\u17c3\u17a2\u1784\u17d2\u1782\u17b6\u179a \u1791\u17b828 \u1781\u17c2\u1780\u1789\u17d2\u1789\u17b6 \u1786\u17d2\u1793\u17b6\u17c62026" / "\u1790\u17d2\u1784\u17c3\u1791\u17b8 28 \u1781\u17c2 \u1780\u1789\u17d2\u1789\u17b6 \u1786\u17d2\u1793\u17b6\u17c6 2026".
# The \u1781\u17c2 / \u1786\u17d2\u1793\u17b6\u17c6 words between the parts defeat DATE_MONTH_NAME.
DATE_KHMER_LONG = re.compile(r"(\d{1,2})\s*\u1781\u17c2\s*([\u1780-\u17ff]+?)\s*\u1786\u17d2\u1793\u17b6\u17c6\s*(\d{4})")

# ----------------------------------------------------------------- sections
ROMAN_SECTION = re.compile(r"^\s*(?P<roman>[IVXL]{1,4})\s*[\.\)]\s*(?P<rest>.*)$")
LEADING_NOISE = re.compile(r"^[\s\-–—•*#>]+|^\s*\d+[\.\)]\s+")

# Heading of the all-categories summary block ("GRAND TOTAL" in generated
# messages). A heading only — the per-category "សរុបរួមចំនួន : 05" line
# carries numbers, so it never matches.
GRAND_TOTAL_HEADER = re.compile(
    r"^(?:grand\s*total|សរុបរួមទាំងអស់|សរុបទាំងអស់|សរុបរួម)\s*[:：]?\s*$",
    re.IGNORECASE,
)

# Words that mark a line as *metric-bearing* rather than a section header.
METRIC_MARKERS = re.compile(
    r"ចំនួន|សរុប|នាក់|ស្រី|\bPP\b|\bKP\b|\btotal\b|\bfemale\b",
    re.IGNORECASE,
)
CATEGORY_TITLE_MARKER = re.compile(r"បានទទួលពាក្យបាក់ឌុប|ទទួលពាក្យ", re.IGNORECASE)

# --------------------------------------------------------------- grade line
#   "-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់"
GRADE_KHMER = re.compile(
    r"(?:និទ្ទេស|ថ្នាក់)\s*[:：\-–—]?\s*(?P<grade>[A-Ea-e])(?![A-Za-z])"
)
#   "Grade D: 3", "grade-d 3"
GRADE_ENGLISH = re.compile(r"\bgrades?\s*[-_]?\s*(?P<grade>[A-Ea-e])(?![A-Za-z])", re.IGNORECASE)
#   "D ចំនួន : 3" / "-D: 3"
GRADE_BARE = re.compile(r"^\s*[-–—•]?\s*(?P<grade>[A-Ea-e])(?![A-Za-z])")

TOTAL_WORDS = r"(?:សរុបរួមចំនួន|ចំនួន|សរុប|total|totals|amount)"
FEMALE_WORDS = r"(?:ស្រីភាព|ស្រី|female|woman|women|girl|girls)"

# Figures may be written "1250", "1,250" or "1 250" depending on who typed them.
NUM = r"\d{1,3}(?:[,\u00a0\u2009 ]\d{3})+|\d+"

TOTAL_ANY = re.compile(rf"(?:{TOTAL_WORDS})\s*[:：]?\s*(?P<value>{NUM})", re.IGNORECASE)
# Khmer puts the label first ("ស្រី 05"), English often puts it after ("4 female").
FEMALE_ANY = re.compile(
    rf"(?:{FEMALE_WORDS})\s*[:：]?\s*(?P<value>{NUM})"
    rf"|(?P<value2>{NUM})\s*(?:{FEMALE_WORDS})\b",
    re.IGNORECASE,
)
ANY_NUMBER = re.compile(NUM)
DATE_LABEL = re.compile(r"^\s*(?:ថ្ងៃទី|date|dated|on|នាទី)\s*[:：]?\s*", re.IGNORECASE)

# ------------------------------------------------------------------- pp/kp
#   "(PP: 01 នាក់ , KP: 00 នាក់)"  and  "PP: 1, KP: 0"
PP_KP_PAIR = re.compile(
    rf"\bPP\s*[:：]?\s*(?P<pp>{NUM})[^A-Za-z0-9]{{0,24}}?\bKP\s*[:：]?\s*(?P<kp>{NUM})",
    re.IGNORECASE,
)
PP_LABEL = re.compile(r"\bPP\b|ពិនិត្យពេញ", re.IGNORECASE)
KP_LABEL = re.compile(r"\bKP\b|គម្នាត", re.IGNORECASE)
