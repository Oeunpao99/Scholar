"""
Deterministic extraction of daily report data from unstructured text.

Handles the canonical Khmer Telegram layout as well as the looser phrasing
staff use on Facebook, WhatsApp and scanned documents.  The parser is
intentionally explainable: every value it returns is traceable to a matched
pattern, and anything it is not certain about is surfaced through
``warnings`` for the reviewer to check before saving.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.models.enums import GRADE_ORDER
from app.schemas.ai import ExtractedCategory, ExtractedGrade, ExtractedReport
from app.services.ai import patterns as P
from app.services.ai.normalizer import (
    KHMER_MONTHS,
    normalize_for_parsing,
    normalize_key,
    split_lines,
    strip_ordinal_marks,
    to_int,
)
from app.services.reference_defaults import CATEGORY_KEYWORDS

# The report always numbers its sections I / II / III in this order.
ROMAN_TO_CATEGORY: dict[str, str] = {
    "I": "current_year",
    "II": "before_current_year",
    "III": "other_province",
    "IV": "other_province",
}

# strip_ordinal_marks also removes Khmer vowel signs ("កញ្ញា" → "កញ្ញ"), so the
# month table is indexed both as written and in its stripped form.
_MONTHS_STRIPPED = {normalize_key(strip_ordinal_marks(k)): v for k, v in KHMER_MONTHS.items()}


def _month_number(raw: str) -> int | None:
    return KHMER_MONTHS.get(normalize_key(raw)) or _MONTHS_STRIPPED.get(
        normalize_key(strip_ordinal_marks(raw))
    )


# How categories are named in (Khmer) user-facing warnings.
_CATEGORY_LABELS = {
    "current_year": "ផ្នែក I",
    "before_current_year": "ផ្នែក II",
    "other_province": "ផ្នែក III",
}

# Keywords sorted longest-first so "មុនឆ្នាំ" wins over the generic "ឆ្នាំ".
_KEYWORD_INDEX: list[tuple[str, str]] = sorted(
    (
        (normalize_key(keyword), code)
        for code, words in CATEGORY_KEYWORDS.items()
        for keyword in words
    ),
    key=lambda item: -len(item[0]),
)

# Too generic to identify a category on their own.
_WEAK_KEYWORDS = {"ឆ្នាំ", "ខេត្ត", "មុន", "year", "province"}


@dataclass(slots=True)
class _Section:
    """Accumulator for one category block found in the text."""

    category: str | None = None
    title: str | None = None
    grades: dict[str, dict[str, int]] = field(default_factory=dict)
    total: int = 0
    female: int = 0
    pp: int = 0
    kp: int = 0
    has_total_line: bool = False
    total_is_cumulative: bool = False
    last_grade: str | None = None

    def grade(self, code: str) -> dict[str, int]:
        self.last_grade = code
        return self.grades.setdefault(code, {"total": 0, "female": 0, "pp": 0, "kp": 0})


class BuiltinExtractor:
    """Rule-based extractor - no network calls, fully deterministic."""

    name = "builtin"

    def extract(
        self,
        text: str,
        *,
        default_date: date | None = None,
        current_year: int | None = None,
    ) -> ExtractedReport:
        raw = normalize_for_parsing(text)
        warnings: list[str] = []

        parsed_date, date_warnings = self._detect_date(raw, current_year)
        warnings.extend(date_warnings)
        date_from_text = parsed_date is not None
        if parsed_date is None:
            parsed_date = default_date
            if default_date is not None:
                warnings.append(f"រកមិនឃើញកាលបរិច្ឆេទក្នុងអត្ថបទ — បានប្រើ {default_date} ជំនួស។")
            else:
                warnings.append("រកមិនឃើញកាលបរិច្ឆេទ — សូមជ្រើសរើសកាលបរិច្ឆេទមុនពេលរក្សាទុក។")

        sections = self._split_sections(raw)
        if not sections:
            warnings.append(
                "រកមិនឃើញតួលេខនិទ្ទេស ឬចំនួនសរុបទេ។ សូមពិនិត្យថាអត្ថបទមានជួរដូចជា "
                "'-និទ្ទេស D ចំនួន : 1 នាក់ ស្រី 0 នាក់'។"
            )
            sections = []

        categories: list[ExtractedCategory] = []
        for section in sections:
            resolved = section.category or self._infer_category(section.title or "")
            if resolved is None:
                resolved = "current_year"
                warnings.append(
                    "មិនអាចកំណត់ផ្នែកនៃប្លុកទិន្នន័យមួយបានទេ — បានដាក់ក្នុងផ្នែក I។ សូមពិនិត្យឡើងវិញ។"
                )
            categories.append(self._to_schema(section, resolved, warnings))

        confidence = self._confidence(
            date_detected=date_from_text,
            categories=categories,
        )
        return ExtractedReport(
            date=parsed_date,
            current_year=current_year,
            categories=categories,
            source_language="km" if _has_khmer(raw) else "en",
            confidence=confidence,
            warnings=warnings,
        )

    # ------------------------------------------------------------------ date
    def _detect_date(self, text: str, current_year: int | None) -> tuple[date | None, list[str]]:
        warnings: list[str] = []

        match = P.DATE_DMY.search(text)
        if match:
            day, month, year = (to_int(g) for g in match.groups())
            candidate = _safe_date(_expand_year(year), month, day)
            if candidate:
                return candidate, warnings
            warnings.append("កាលបរិច្ឆេទដំបូងក្នុងអត្ថបទមិនត្រឹមត្រូវ ហើយត្រូវបានរំលង។")

        match = P.DATE_YMD.search(text)
        if match:
            year, month, day = (to_int(g) for g in match.groups())
            candidate = _safe_date(year, month, day)
            if candidate:
                return candidate, warnings

        for match in [*P.DATE_KHMER_LONG.finditer(text), *P.DATE_MONTH_NAME.finditer(text)]:
            day_raw, month_raw, year_raw = match.groups()
            month = _month_number(month_raw)
            if month:
                candidate = _safe_date(to_int(year_raw), month, to_int(day_raw))
                if candidate:
                    return candidate, warnings

        if current_year and re.search(rf"\b{current_year}\b", text):
            warnings.append(
                f"រកឃើញតែឆ្នាំ {current_year} — មិនឃើញថ្ងៃ និងខែទេ។"
            )
        return None, warnings

    # -------------------------------------------------------------- sections
    def _split_sections(self, text: str) -> list[_Section]:
        sections: list[_Section] = []
        current: _Section | None = None

        for raw_line in split_lines(text):
            line = P.LEADING_NOISE.sub("", raw_line).strip()
            if not line:
                continue

            # A bare date is handled once, up front. Left in the stream it would
            # open a phantom section and its numbers would be read as a total.
            if self._is_date_only(line):
                continue

            # The grand-total block sums every category. Read into a detached
            # section that is never returned, so its figures are not merged
            # into the preceding category (they used to land in III.).
            if P.GRAND_TOTAL_HEADER.match(line):
                current = _Section()
                continue

            header = self._as_header(line)
            if header is not None:
                current = header
                sections.append(current)
                continue

            if current is None:
                current = _Section()
                sections.append(current)
            self._consume_line(current, line)

        populated = [s for s in sections if s.grades or s.has_total_line]
        return populated

    @staticmethod
    def _is_date_only(line: str) -> bool:
        stripped = P.DATE_LABEL.sub("", line).strip()
        if P.DATE_DMY.fullmatch(stripped) or P.DATE_YMD.fullmatch(stripped):
            return True
        # A written-out date line ("ថ្ងៃទី28 ខែកញ្ញា ឆ្នាំ2026") with no counts on
        # it. Otherwise its day number (28) was read as a student total.
        has_written_date = P.DATE_KHMER_LONG.search(stripped) or P.DATE_MONTH_NAME.search(stripped)
        return bool(has_written_date) and not P.METRIC_MARKERS.search(stripped)

    def _as_header(self, line: str) -> _Section | None:
        """Return a new section when ``line`` looks like a category heading."""
        roman_match = P.ROMAN_SECTION.match(line)
        if roman_match:
            code = ROMAN_TO_CATEGORY.get(roman_match.group("roman").upper())
            rest = roman_match.group("rest").strip()
            if code and rest:
                return _Section(category=code, title=rest)

        if P.METRIC_MARKERS.search(line):
            return None

        code = self._infer_category(line)
        if code:
            return _Section(category=code, title=line)
        return None

    def _infer_category(self, text: str) -> str | None:
        if not text:
            return None
        lowered = normalize_key(text)
        for keyword, code in _KEYWORD_INDEX:
            if not keyword or keyword not in lowered:
                continue
            if keyword in _WEAK_KEYWORDS:
                continue
            return code
        if P.CATEGORY_TITLE_MARKER.search(lowered):
            return "current_year"
        return None

    # ----------------------------------------------------------------- lines
    def _consume_line(self, section: _Section, line: str) -> None:
        grade = self._detect_grade(line)
        pp_kp = P.PP_KP_PAIR.search(line)

        if grade is not None:
            bucket = section.grade(grade)
            total, female = self._extract_total_female(line)
            bucket["total"] = total
            bucket["female"] = female
            if pp_kp is not None:
                bucket["pp"] = to_int(pp_kp.group("pp"))
                bucket["kp"] = to_int(pp_kp.group("kp"))
            return

        if pp_kp is not None:
            pp = to_int(pp_kp.group("pp"))
            kp = to_int(pp_kp.group("kp"))
            bucket = section.grades.get(section.last_grade) if section.last_grade else None
            if bucket is not None and not (bucket["pp"] or bucket["kp"]):
                # The report format puts PP/KP on the line after the grade it
                # belongs to, so attribute the pair to that grade.
                bucket["pp"] = pp
                bucket["kp"] = kp
            else:
                section.pp = pp
                section.kp = kp
            return

        total, female = self._extract_total_female(line)
        if total < 0:
            return
        section.total = total
        section.female = female
        section.has_total_line = True
        # "សរុបរួម…" is the template's CUMULATIVE line, not today's gain.
        section.total_is_cumulative = "សរុបរួម" in line
        # Anything after the summary line belongs to the category, not a grade.
        section.last_grade = None

    def _detect_grade(self, line: str) -> str | None:
        for pattern in (P.GRADE_KHMER, P.GRADE_ENGLISH, P.GRADE_BARE):
            match = pattern.search(line)
            if match:
                code = match.group("grade").upper()
                if code in GRADE_ORDER:
                    return code
        return None

    def _extract_total_female(self, line: str) -> tuple[int, int]:
        """Return ``(total, female)``; ``total`` is ``-1`` when nothing matched."""
        female_match = P.FEMALE_ANY.search(line)
        if female_match is None:
            female = 0
        else:
            female = to_int(female_match.group("value") or female_match.group("value2"))

        total_match = P.TOTAL_ANY.search(line)
        if total_match:
            return to_int(total_match.group("value")), female

        numbers = [to_int(n) for n in P.ANY_NUMBER.findall(line)]
        if not numbers:
            return -1, 0
        if female_match and numbers[0] == female and len(numbers) > 1:
            return numbers[1], female
        return numbers[0], female

    # ---------------------------------------------------------------- output
    @staticmethod
    def _to_schema(
        section: _Section, category_code: str, warnings: list[str]
    ) -> ExtractedCategory:
        label = _CATEGORY_LABELS.get(category_code, category_code)
        grades = [
            ExtractedGrade(
                grade=code,  # type: ignore[arg-type]
                total=values["total"],
                female=values["female"],
                pp=values["pp"],
                kp=values["kp"],
            )
            for code, values in sorted(
                section.grades.items(), key=lambda item: GRADE_ORDER.index(item[0])
            )
            if any(values.values())
        ]

        if grades:
            total = sum(g.total for g in grades)
            female = sum(g.female for g in grades)
            # Grade-level PP/KP win when any grade carries them. Only fall back
            # to the category line when the text gave no grade-level split at
            # all - a genuine zero must not be replaced by a category figure.
            grade_pp = sum(g.pp for g in grades)
            grade_kp = sum(g.kp for g in grades)
            if grade_pp or grade_kp or not (section.pp or section.kp):
                pp, kp = grade_pp, grade_kp
            else:
                pp, kp = section.pp, section.kp
            # The summary line is a cumulative figure, so it is never stored as
            # today's gain. Surface a disagreement instead of dropping it, since
            # a mismatch usually means a grade line was missed.
            if section.has_total_line and section.total and section.total != total:
                warnings.append(
                    f"{label}: និទ្ទេសបូកបាន {total} នាក់ ប៉ុន្តែជួរសរុបសរសេរ {section.total} "
                    "(ទំនងជាចំនួនកើនសន្សំ)។ បាននាំចូលតែតួលេខតាមនិទ្ទេសប៉ុណ្ណោះ។"
                )
        elif section.total_is_cumulative:
            # Template layout with no grade lines = nobody new today. The
            # "សរុបរួម" figure is the running total; importing it as today's gain
            # would double-count every earlier student.
            total = female = pp = kp = 0
        else:
            total = section.total
            female = section.female
            pp = section.pp
            kp = section.kp
            if total or female or pp or kp:
                warnings.append(
                    f"{label}: មានតែចំនួនសរុប គ្មានការបែងចែកតាមនិទ្ទេសទេ។ សូមកំណត់និទ្ទេសមុនពេលរក្សាទុក។"
                )

        if total < 0:
            total = 0
        if female > total:
            warnings.append(f"{label}: ចំនួនស្រី ({female}) លើសចំនួនសរុប ({total})។")
        if pp + kp > total and total:
            warnings.append(f"{label}: ភ្នំពេញ + ខេត្ត ({pp + kp}) លើសចំនួនសរុប ({total})។")

        return ExtractedCategory(
            category=category_code,
            title=section.title,
            grades=grades,
            total=total,
            female=female,
            male=max(total - female, 0),
            pp=pp,
            kp=kp,
        )

    @staticmethod
    def _confidence(*, date_detected: bool, categories: list[ExtractedCategory]) -> float:
        # Nothing recognised means nothing to trust - never hand back a floor
        # score that a reviewer would read as "probably fine".
        if not categories:
            return 0.0
        score = 0.35
        if date_detected:
            score += 0.2
        if any(c.grades for c in categories):
            score += 0.35
        if all(c.category for c in categories):
            score += 0.1
        return round(min(score, 1.0), 2)


def _expand_year(year: int) -> int:
    return year + 2000 if year < 100 else year


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _has_khmer(text: str) -> bool:
    return bool(re.search(r"[\u1780-\u17ff]", text))
