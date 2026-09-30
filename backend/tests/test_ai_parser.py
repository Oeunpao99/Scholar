"""AI/OCR text extraction.

The most important property is the round trip: whatever
``TelegramReportGenerator`` produces must be parseable back into the same
numbers by the deterministic extractor. Everything else (loose phrasing,
missing dates, impossible values) has to be surfaced as a warning rather than
silently guessed.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.schemas.common import Counters
from app.services.ai.builtin_extractor import BuiltinExtractor
from app.services.telegram_generator import build_report

REPORT_DATE = date(2026, 9, 29)
CURRENT_YEAR = 2026


@pytest.fixture
def extractor() -> BuiltinExtractor:
    return BuiltinExtractor()


def grades_by_code(category) -> dict[str, object]:
    """``ExtractedCategory.grades`` is a list; tests index it by grade letter."""
    return {g.grade: g for g in category.grades}


# ------------------------------------------------------ round-trip guarantee
def test_parses_back_its_own_output(extractor: BuiltinExtractor):
    text = build_report(
        report_date=REPORT_DATE,
        categories=[
            {
                "roman_numeral": "I.",
                "title": "បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026",
                "today_grades": {
                    "D": Counters(total=1, female=0, pp=1, kp=0),
                    "E": Counters(total=4, female=2, pp=1, kp=1),
                },
                "cumulative": Counters(total=12, female=5, pp=8, kp=4),
            },
            {
                "roman_numeral": "II.",
                "title": "បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026",
                "today_grades": {"A": Counters(total=3, female=2, pp=0, kp=1)},
                "cumulative": Counters(total=7, female=4, pp=2, kp=1),
            },
        ],
    )

    result = extractor.extract(text, current_year=CURRENT_YEAR)

    assert result.date == REPORT_DATE
    assert len(result.categories) == 2

    first = result.categories[0]
    assert first.category == "current_year"
    first_grades = grades_by_code(first)
    assert first_grades["D"].total == 1
    assert first_grades["D"].pp == 1
    assert first_grades["D"].kp == 0
    assert first_grades["E"].total == 4
    assert first_grades["E"].female == 2
    # ``total`` is today's gain (the sum of the grades), never the cumulative
    # figure printed on the summary line.
    assert first.total == 5
    assert first.pp == 2
    assert first.kp == 1

    second = result.categories[1]
    assert second.category == "before_current_year"
    assert grades_by_code(second)["A"].total == 3
    assert second.total == 3


def test_cumulative_summary_line_is_never_taken_as_todays_gain(extractor: BuiltinExtractor):
    text = build_report(
        report_date=REPORT_DATE,
        categories=[
            {
                "roman_numeral": "I.",
                "title": "បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026",
                "today_grades": {"D": Counters(total=1, female=0, pp=1, kp=0)},
                "cumulative": Counters(total=12, female=5, pp=8, kp=4),
            }
        ],
    )
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    assert result.categories[0].total == 1
    assert any("ជួរសរុប" in w for w in result.warnings)


def test_grand_total_block_is_not_merged_into_the_last_category(extractor: BuiltinExtractor):
    # Exact shape of the Telegram Center output (include_grand_total=True).
    text = (
        "30/09/2026\n\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស D ចំនួន : 2 នាក់ ស្រី 1 នាក់\n"
        "(PP: 1 នាក់ , KP: 1 នាក់)\n"
        "សរុបរួមចំនួន : 5 នាក់ ស្រី 4 នាក់\n"
        "(PP: 2 នាក់, KP: 3 នាក់)\n\n"
        "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026\n"
        "សរុបរួមចំនួន : 0 នាក់ ស្រី 0 នាក់\n"
        "(PP: 0 នាក់, KP: 0 នាក់)\n\n"
        "III. បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង\n"
        "សរុបរួមចំនួន : 0 នាក់ ស្រី 0 នាក់\n"
        "(PP: 0 នាក់, KP: 0 នាក់)\n\n"
        "GRAND TOTAL\n"
        "សរុបរួមចំនួន : 5 នាក់ ស្រី 4 នាក់\n"
        "(PP: 2 នាក់, KP: 3 នាក់)\n"
    )
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    by_code = {c.category: c for c in result.categories}
    assert by_code["current_year"].total == 2
    # Previously the GRAND TOTAL figures (5 / 4 / 2 / 3) were read as category III.
    assert by_code.get("other_province") is None or by_code["other_province"].total == 0


@pytest.mark.parametrize(
    "header",
    [
        "ថ្ងៃទី28 ខែកញ្ញា ឆ្នាំ2026",
        "ថ្ងៃអង្គារ ទី 28 ខែ កញ្ញា ឆ្នាំ 2026",
        "ថ្ងៃទី២៨ ខែកញ្ញា ឆ្នាំ២០២៦",
    ],
)
def test_written_khmer_date_is_detected_and_not_read_as_a_total(extractor: BuiltinExtractor, header: str):
    text = (
        f"{header}\n\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស D ចំនួន : 01នាក់ ស្រី 00នាក់\n"
        "(PP:00នាក់, KP:01នាក់)\n"
    )
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    assert result.date == date(2026, 9, 28)
    # The day "28" used to open a phantom block imported as +28 students.
    assert [c.category for c in result.categories] == ["current_year"]
    assert result.categories[0].total == 1


def test_cumulative_only_category_counts_as_zero_gain_today(extractor: BuiltinExtractor):
    text = (
        "30/09/2026\n"
        "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026\n"
        "សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់\n"
        "(PP: 08 នាក់, KP: 04 នាក់)\n"
    )
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    # No grade lines today → nobody new; 12 is the running total, not a gain.
    assert all(c.total == 0 for c in result.categories)


def test_consistent_summary_line_raises_no_warning(extractor: BuiltinExtractor):
    result = extractor.extract(
        "29/09/2026\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស D ចំនួន : 02 នាក់ ស្រី 01 នាក់\n"
        "(PP: 01 នាក់ , KP: 00 នាក់)\n"
        "(PP: 01 នាក់, KP: 00 នាក់)\n",
        current_year=CURRENT_YEAR,
    )
    assert result.categories[0].total == 2
    assert not any("ជួរសរុប" in w for w in result.warnings)


def test_roman_numerals_map_to_the_right_categories(extractor: BuiltinExtractor):
    text = (
        "01/01/2026\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស A ចំនួន : 01 នាក់ ស្រី 01 នាក់\n"
        "(PP: 00 នាក់ , KP: 00 នាក់)\n"
        "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026\n"
        "-និទ្ទេស B ចំនួន : 02 នាក់ ស្រី 00 នាក់\n"
        "(PP: 01 នាក់ , KP: 00 នាក់)\n"
        "III. បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង\n"
        "-និទ្ទេស C ចំនួន : 03 នាក់ ស្រី 01 នាក់\n"
        "(PP: 01 នាក់ , KP: 01 នាក់)\n"
    )
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    assert [c.category for c in result.categories] == [
        "current_year",
        "before_current_year",
        "other_province",
    ]


# ----------------------------------------------------------------- date
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("29/09/2026 និទ្ទេស A", date(2026, 9, 29)),
        ("2026-09-29 និទ្ទេស A", date(2026, 9, 29)),
        ("29-09-2026 និទ្ទេស A", date(2026, 9, 29)),
    ],
)
def test_detects_common_date_formats(extractor: BuiltinExtractor, text: str, expected: date):
    result = extractor.extract(text, current_year=CURRENT_YEAR)
    assert result.date == expected


def test_two_digit_year_is_expanded_to_the_current_century(extractor: BuiltinExtractor):
    result = extractor.extract("05/01/26 និទ្ទេស A", current_year=CURRENT_YEAR)
    assert result.date == date(2026, 1, 5)


def test_falls_back_to_the_supplied_date(extractor: BuiltinExtractor):
    result = extractor.extract("និទ្ទេស A ចំនួន 1", default_date=date(2026, 5, 1))
    assert result.date == date(2026, 5, 1)
    assert any("ជំនួស" in w for w in result.warnings)


def test_missing_date_with_no_fallback_is_flagged(extractor: BuiltinExtractor):
    result = extractor.extract("និទ្ទេស A ចំនួន 1")
    assert result.date is None
    assert any("រកមិនឃើញកាលបរិច្ឆេទ" in w for w in result.warnings)


def test_impossible_date_is_rejected(extractor: BuiltinExtractor):
    result = extractor.extract("31/02/2026 និទ្ទេស A", default_date=date(2026, 1, 1))
    assert result.date == date(2026, 1, 1)
    assert any("មិនត្រឹមត្រូវ" in w for w in result.warnings)


# ------------------------------------------------------------- quantities
def test_grade_figures_are_read(extractor: BuiltinExtractor):
    result = extractor.extract(
        "01/01/2026\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស C ចំនួន : 11 នាក់ ស្រី 04 នាក់\n"
        "(PP: 07 នាក់ , KP: 03 នាក់)\n",
        current_year=CURRENT_YEAR,
    )
    grade = grades_by_code(result.categories[0])["C"]
    assert (grade.total, grade.female, grade.pp, grade.kp) == (11, 4, 7, 3)


def test_english_style_input_is_understood(extractor: BuiltinExtractor):
    result = extractor.extract(
        "Date: 29/09/2026\n"
        "Current year\n"
        "Grade A: 10 students, 4 female\n"
        "PP: 3, KP: 2\n",
        current_year=CURRENT_YEAR,
    )
    assert result.date == REPORT_DATE
    assert result.categories[0].category == "current_year"
    assert grades_by_code(result.categories[0])["A"].total == 10
    assert grades_by_code(result.categories[0])["A"].female == 4


def test_numbers_with_thousands_separators_are_read(extractor: BuiltinExtractor):
    result = extractor.extract(
        "29/09/2026\nI. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស A ចំនួន : 1,250 នាក់ ស្រី 640 នាក់\n",
        current_year=CURRENT_YEAR,
    )
    assert grades_by_code(result.categories[0])["A"].total == 1250
    assert grades_by_code(result.categories[0])["A"].female == 640


# ------------------------------------------------------------- robustness
def test_empty_text_produces_no_categories_and_a_warning(extractor: BuiltinExtractor):
    result = extractor.extract("", default_date=REPORT_DATE)
    assert result.categories == []
    assert any("រកមិនឃើញតួលេខ" in w for w in result.warnings)
    assert result.confidence == 0.0


def test_unlabelled_block_is_flagged_for_review(extractor: BuiltinExtractor):
    result = extractor.extract(
        "01/01/2026\n-និទ្ទេស A ចំនួន : 05 នាក់ ស្រី 01 នាក់\n",
        current_year=CURRENT_YEAR,
    )
    assert any("មិនអាចកំណត់ផ្នែក" in w for w in result.warnings)


def test_high_confidence_for_clean_input(extractor: BuiltinExtractor):
    result = extractor.extract(
        "29/09/2026\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស D ចំនួន : 02 នាក់ ស្រី 01 នាក់\n"
        "(PP: 01 នាក់ , KP: 00 នាក់)\n",
        current_year=CURRENT_YEAR,
    )
    assert result.confidence > 0.8
    assert result.warnings == []


def test_khmer_input_is_tagged_as_khmer(extractor: BuiltinExtractor):
    result = extractor.extract(
        "29/09/2026\nI. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស A ចំនួន : 01 នាក់ ស្រី 00 នាក់\n",
        current_year=CURRENT_YEAR,
    )
    assert result.source_language == "km"


def test_extraction_is_deterministic(extractor: BuiltinExtractor):
    text = (
        "29/09/2026\nI. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស A ចំនួន : 01 នាក់ ស្រី 00 នាក់\n"
        "-និទ្ទេស B ចំនួន : 09 នាក់ ស្រី 03 នាក់\n"
    )
    runs = [extractor.extract(text, current_year=CURRENT_YEAR) for _ in range(5)]
    assert all(r.model_dump() == runs[0].model_dump() for r in runs)
