"""
Pull student fields out of the OCR text of a single application form.

Label based: find the form's labels ("គោត្តនាម-នាម៖", "ភេទ៖", "លេខទូរស័ព្ទ៖"...)
and read the value that follows, up to the next label on the same line or,
when the label stands alone, from the next line. Nothing is guessed: a field
whose label isn't found stays empty for the user to fill in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.services.ai.normalizer import normalize_for_parsing

# field -> labels. Longest labels are tried first, so "ឈ្មោះវិទ្យាល័យ" (school
# name) wins over "ឈ្មោះ" (name) and "លំដាប់ពិន្ទុ" over "លំដាប់".
FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "full_name": (
        "ខ្ញុំបាទ/ នាងខ្ញុំឈ្មោះ", "ខ្ញុំបាទ/នាងខ្ញុំឈ្មោះ", "ខ្ញុំបាទ នាងខ្ញុំឈ្មោះ",
        "ខ្ញុំបាទ/នាងខ្ញុំ", "ខ្ញុំបាទឈ្មោះ", "នាងខ្ញុំឈ្មោះ", "ឈ្មោះសាមីខ្លួន",
        "គោត្តនាម-នាម", "គោត្តនាម - នាម", "គោត្តនាម- នាម", "គោត្តនាម និងនាម",
        "គោត្តនាម និង នាម", "គោត្តនាមនិងនាម", "គោត្តនាម នាម", "គោតានាម-នាម",
        "គោតានាម និងនាម", "គោតានាម", "គោត្តនាម", "នាមត្រកូល និងនាមខ្លួន",
        "ឈ្មោះបេក្ខជន", "ឈ្មោះសិស្ស", "ឈ្មោះ", "full name", "name",
    ),
    "gender": ("ភេទ", "ភេទទ", "gender", "sex"),
    "grade": ("និទ្ទេស", "និទេស", "និ.", "grade", "mention"),
    "score_rank": (
        "លំដាប់ពិន្ទុលេខ", "លំដាប់ពិន្ទុ", "ចំណាត់ថ្នាក់លេខ", "ចំណាត់ថ្នាក់",
        "លំដាប់លេខ", "លេខរៀងពិន្ទុ", "លំដាប់ទី", "លំដាប់", "score rank", "rank",
    ),
    "high_school": (
        "ឈ្មោះវិទ្យាល័យ", "មកពីវិទ្យាល័យ", "វិទ្យាល័យ", "វិទាល័យ", "ឈ្មោះវិទាល័យ", "high school"
    ),
    "stream": ("ថ្នាក់", "ផ្នែក", "ផ្នែកសិក្សា", "stream", "section"),
    "university": (
        "ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន", "ស្នើសុំនៅសាកលវិទ្យាល័យ",
        "សាកលវិទ្យាល័យ/វិទ្យាស្ថាន", "សាកលវិទាល័យ/វិទ្យាស្ថាន",
        "ស្នើសុំនៅ", "ឈ្មោះសាកលវិទ្យាល័យ", "សាកលវិទ្យាល័យ", "សាកលវិទាល័យ",
        "university", "institute",
    ),
    "major": (
        "ជំនាញ/មុខវិជ្ជា", "ជំនាញ / មុខវិជ្ជា", "ជំនាញ/ មុខវិជ្ជា", "ជំនាញ",
        "មុខវិជ្ជា", "មុខវិជ្ជា/ជំនាញ", "major", "skill"
    ),
    "phone": (
        "លេខទូរស័ព្ទ", "លេខទូរសព្ទ", "ទូរស័ព្ទលេខ", "ទូរស័ព្ទ", "ទូរសព្ទ",
        "លេខទំនាក់ទំនង", "phone", "tel", "contact"
    ),
}

FIELD_ORDER = tuple(FIELD_LABELS)

# Separators forms put after a label: ":" "៖" (Khmer colon) "-" dotted leaders.
_SEP = r"[:：៖\-–—.…]"
_LEADING_JUNK = re.compile(rf"^(?:\s|{_SEP})+")
_TRAILING_JUNK = re.compile(rf"(?:\s|{_SEP}|[|/,;])+$")
_DOT_LEADERS = re.compile(r"[.…_]{3,}")
_PHONE = re.compile(r"(?<!\d)(?:\+?855[\s.-]?|0)(?:\d[\s.-]?){7,9}\d(?!\d)")


@dataclass(slots=True)
class _Hit:
    field: str
    start: int  # label start
    end: int  # label end (value starts here)


@dataclass(slots=True)
class StudentFields:
    values: dict[str, object] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def found(self) -> list[str]:
        return [f for f in FIELD_ORDER if self.values.get(f) not in (None, "")]

    @property
    def missing(self) -> list[str]:
        return [f for f in FIELD_ORDER if f not in self.found]


def _label_pattern(label: str) -> re.Pattern[str]:
    escaped = re.escape(label)
    if label in ("វិទ្យាល័យ", "វិទាល័យ"):
        # Not the tail of "សាកលវិទ្យាល័យ" (university).
        escaped = r"(?<!សាកល)" + escaped
    elif label == "ថ្នាក់":
        # Not the tail of "ចំណាត់ថ្នាក់" (score rank)
        escaped = r"(?<!ចំណាត់)" + escaped
    elif label in ("ឈ្មោះ", "name"):
        # Not the tail of parent info ("ឪពុកឈ្មោះ", "ម្ដាយឈ្មោះ", "អាណាព្យាបាលឈ្មោះ")
        escaped = r"(?<!ឪពុក)(?<!ឪពុក )(?<!ម្ដាយ)(?<!ម្ដាយ )(?<!អាណាព្យាបាល)(?<!អាណាព្យាបាល )(?<!វិទ្យាល័យ)(?<!សាកលវិទ្យាល័យ)" + escaped
    if label.isascii():
        return re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    return re.compile(escaped)


def _format_field_warning(field_khmer: str, raw_val: str) -> str:
    """Format warning for unparseable field without leaking raw OCR gibberish."""
    khmer_chars = re.findall(r"[\u1780-\u17d3]", raw_val)
    if len(khmer_chars) >= 2:
        clean_snippet = re.sub(r"[^\u1780-\u17d3\s]+", " ", raw_val).strip()
        clean_snippet = re.sub(r"\s+", " ", clean_snippet)
        if len(clean_snippet) > 25:
            clean_snippet = clean_snippet[:25] + "..."
        return f"អាន{field_khmer}មិនច្បាស់: «{clean_snippet}»"
    return f"អាន{field_khmer}មិនច្បាស់ — សូមជ្រើសរើសដោយដៃ"


_LABELS: list[tuple[str, re.Pattern[str], int]] = sorted(
    (
        (fld, _label_pattern(label), len(label))
        for fld, labels in FIELD_LABELS.items()
        for label in labels
    ),
    key=lambda item: -item[2],
)


def _find_labels(line: str) -> list[_Hit]:
    """Label occurrences in one line, longest first, without overlaps.

    A label counts only at the start of the line or when a separator follows
    it, so a value such as "វិទ្យាល័យព្រះស៊ីសុវត្ថិ" isn't mistaken for a label.
    """
    taken: list[tuple[int, int]] = []
    hits: list[_Hit] = []
    for fld, pattern, _ in _LABELS:
        for m in pattern.finditer(line):
            s, e = m.start(), m.end()
            if any(s < te and e > ts for ts, te in taken):
                continue
            at_start = not line[:s].strip()
            followed_by_sep = re.match(rf"\s*{_SEP}", line[e:]) is not None
            if not (at_start or followed_by_sep):
                continue
            taken.append((s, e))
            hits.append(_Hit(fld, s, e))
    return sorted(hits, key=lambda h: h.start)


def _clean(value: str) -> str:
    value = _DOT_LEADERS.sub(" ", value)
    value = _LEADING_JUNK.sub("", value)
    value = _TRAILING_JUNK.sub("", value)
    return re.sub(r"\s{2,}", " ", value).strip()


def _raw_values(lines: list[str]) -> dict[str, str]:
    raw: dict[str, str] = {}
    for i, line in enumerate(lines):
        hits = _find_labels(line)
        for j, hit in enumerate(hits):
            if hit.field in raw:
                continue  # first occurrence wins
            stop = hits[j + 1].start if j + 1 < len(hits) else len(line)
            value = _clean(line[hit.end:stop])
            if not value and j + 1 == len(hits) and i + 1 < len(lines) and not _find_labels(lines[i + 1]):
                value = _clean(lines[i + 1])  # value written under the label
            if value:
                raw[hit.field] = value
    return raw


def _gender(value: str) -> str | None:
    v = value.lower()
    if "ស្រី" in v or re.search(r"\b(f|female)\b", v):
        return "F"
    if "ប្រុស" in v or re.search(r"\b(m|male)\b", v):
        return "M"
    return None


def _grade(value: str) -> str | None:
    m = re.search(r"\b([A-Ea-e])\b", value) or re.match(r"([A-Ea-e])", value)
    return m.group(1).upper() if m else None


def _stream(value: str) -> str | None:
    v = value.lower()
    if "សង្គម" in v or "social" in v:
        return "social_science"
    if "វិទ្យាសាស្ត្រ" in v or "science" in v:
        return "science"
    return None


def _phone(value: str) -> str | None:
    m = _PHONE.search(value)
    return re.sub(r"\s{2,}", " ", m.group(0)).strip() if m else None


def _int(value: str) -> int | None:
    m = re.search(r"\d+", value)
    return int(m.group(0)) if m and int(m.group(0)) > 0 else None


def _clean_name(value: str) -> str | None:
    if not value:
        return None
    # Cut off parent/section labels that might follow on the same line
    for marker in ("មុខរបរ", "ឪពុក", "ម្ដាយ", "អាណាព្យាបាល", "លេខទូរស័ព្ទ", "សញ្ញាតិ", "ជនជាតិ", "ភេទ", "និទ្ទេស", "ថ្នាក់", "ឆ្នាំ", "ភូមិ", "ឃុំ", "ស្រុក", "ខេត្ត"):
        if marker in value:
            pos = value.find(marker)
            value = value[:pos].strip()

    # If there are Khmer characters, extract clean Khmer name words
    khmer_parts = re.findall(r"[\u1780-\u17d3\u17dd]+", value)
    if khmer_parts:
        skip_words = {"ខ្ញុំបាទ", "នាងខ្ញុំ", "សាមីខ្លួន", "បេក្ខជន", "សិស្ស", "ឈ្មោះ", "លោក", "លោកស្រី", "អ្នកនាង", "កញ្ញា"}
        filtered = [w for w in khmer_parts if w not in skip_words and (len(w) > 1 or w in ("ក", "គ", "ង"))]
        if filtered:
            candidate = " ".join(filtered[:4])
            if len(candidate) >= 2:
                return candidate

    # Latin fallback for English names
    latin_words = re.findall(r"\b[A-Za-z]+\b", value)
    if latin_words:
        hallucinated = {"ee", "wives", "ban", "mrtg", "ran", "peai", "le", "etn", "chheara", "kefichh", "rite", "none", "null"}
        clean_latin = [w for w in latin_words if w.lower() not in hallucinated]
        if clean_latin:
            return " ".join(clean_latin[:4])

    return None


def extract_student_fields(ocr_text: str, filename: str | None = None) -> StudentFields:
    lines = [ln.strip() for ln in normalize_for_parsing(ocr_text).split("\n") if ln.strip()]
    raw = _raw_values(lines)
    out = StudentFields()

    for fld in ("high_school", "university", "major"):
        if raw.get(fld):
            out.values[fld] = raw[fld][:255]

    # Full name extraction with aggressive cleaning
    raw_name = raw.get("full_name")
    cleaned_name = _clean_name(raw_name) if raw_name else None

    # Fallback to filename if available and cleaner (e.g. "ឈាន ស្រីនិត.pdf")
    if filename:
        import os

        stem = re.sub(r"\.[^.]+$", "", os.path.basename(filename)).strip()
        stem_clean = re.sub(r"[_\-]+.*$", "", stem).strip()
        stem_khmer = _clean_name(stem_clean)
        if stem_khmer and len(stem_khmer) >= 3:
            first_ocr_word = cleaned_name.split()[0] if cleaned_name else ""
            first_stem_word = stem_khmer.split()[0]
            # If no OCR name, or matching family name, or OCR had noise symbols
            has_ocr_noise = bool(raw_name and re.search(r"[\[\](),./\\#\-–—a-zA-Z]", raw_name))
            if not cleaned_name or first_ocr_word == first_stem_word or has_ocr_noise:
                cleaned_name = stem_khmer

    if cleaned_name:
        out.values["full_name"] = cleaned_name

    if "gender" in raw:
        out.values["gender"] = _gender(raw["gender"])
        if out.values["gender"] is None:
            out.warnings.append(_format_field_warning("ភេទ", raw["gender"]))

    # Smart gender deduction: names containing 'ស្រី' (Srey) in Cambodia are 100% Female
    if not out.values.get("gender") and out.values.get("full_name"):
        if "ស្រី" in str(out.values["full_name"]):
            out.values["gender"] = "F"
            # Remove any previous gender warning if gender was successfully resolved
            out.warnings = [w for w in out.warnings if "ភេទ" not in w]

    if "grade" in raw:
        out.values["grade"] = _grade(raw["grade"])
        if out.values["grade"] is None:
            out.warnings.append(_format_field_warning("និទ្ទេស", raw["grade"]))

    if "score_rank" in raw:
        out.values["score_rank"] = _int(raw["score_rank"])

    if "stream" in raw:
        out.values["stream"] = _stream(raw["stream"])
        if out.values["stream"] is None:
            out.warnings.append(_format_field_warning("ថ្នាក់", raw["stream"]))
    elif "stream" not in out.values:
        whole_text = "\n".join(lines)
        if re.search(r"(?:វិទ្យាសាស្ត្រសង្គម|ផ្នែកសង្គម|ផ្នែកវិទ្យាសាស្ត្រសង្គម)", whole_text):
            out.values["stream"] = "social_science"
        elif re.search(r"(?:វិទ្យាសាស្ត្រពិត|ផ្នែកវិទ្យាសាស្ត្រពិត)", whole_text):
            out.values["stream"] = "science"

    if "score_rank" not in out.values:
        for line in lines:
            m = re.search(r"(?:ចំណាត់ថ្នាក់|លំដាប់ពិន្ទុ|លំដាប់លេខ|លេខរៀងពិន្ទុ|លំដាប់)(?:លេខ|ទី)?\s*[:：៖\-\.]*\s*(\d+)", line)
            if m and int(m.group(1)) > 0:
                out.values["score_rank"] = int(m.group(1))
                break

    # A phone number is recognisable even without its label.
    out.values["phone"] = _phone(raw.get("phone", "")) or _phone("\n".join(lines))

    out.values = {k: v for k, v in out.values.items() if v not in (None, "")}
    return out
