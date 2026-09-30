"""Telegram message formatting.

The ministry requires an exact layout. These tests pin every character that
matters: zero padding, the two different comma spacings around PP/KP, the fact
that grade lines show only today's gain, and the fact that the total line shows
cumulative figures.
"""

from __future__ import annotations

from datetime import date

from app.schemas.common import Counters
from app.services.telegram_generator import (
    TelegramReportGenerator,
    build_report,
)

REPORT_DATE = date(2026, 9, 29)


def cat(
    roman: str,
    title: str,
    today_grades: dict[str, Counters],
    cumulative: Counters,
) -> dict:
    return {
        "roman_numeral": roman,
        "title": title,
        "today_grades": today_grades,
        "cumulative": cumulative,
    }


CATEGORIES = [
    cat(
        "I.",
        "បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026",
        {"D": Counters(total=1, female=0, pp=1, kp=0)},
        Counters(total=12, female=5, pp=8, kp=4),
    ),
    cat(
        "II.",
        "បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026",
        {"A": Counters(total=3, female=2, pp=0, kp=1)},
        Counters(total=7, female=4, pp=2, kp=1),
    ),
    cat("III.", "បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង", {}, Counters()),
]


# ------------------------------------------------------------------ numbering
def test_numbers_are_zero_padded_to_two_digits():
    gen = TelegramReportGenerator()
    assert gen.num(0) == "00"
    assert gen.num(1) == "01"
    assert gen.num(9) == "09"
    assert gen.num(10) == "10"
    assert gen.num(100) == "100"


def test_zero_padding_can_be_disabled():
    gen = TelegramReportGenerator(zero_pad=False)
    assert gen.num(1) == "1"
    assert gen.num(0) == "0"


# ---------------------------------------------------------------- line shapes
def test_grade_line_matches_required_text():
    gen = TelegramReportGenerator()
    line = gen.grade_line("D", Counters(total=1, female=0, pp=1, kp=0))
    assert line == "-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់"


def test_grade_pp_kp_line_has_space_before_comma():
    gen = TelegramReportGenerator()
    line = gen.grade_pp_kp_line(Counters(total=1, female=0, pp=1, kp=0))
    assert line == "(PP: 01 នាក់ , KP: 00 នាក់)"


def test_total_pp_kp_line_has_no_space_before_comma():
    gen = TelegramReportGenerator()
    line = gen.total_pp_kp_line(Counters(total=12, female=5, pp=8, kp=4))
    assert line == "(PP: 08 នាក់, KP: 04 នាក់)"


def test_total_line_shows_the_numbers_it_is_given():
    gen = TelegramReportGenerator()
    line = gen.total_line(Counters(total=12, female=5, pp=8, kp=4))
    assert line == "សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់"


# ------------------------------------------------------------- block content
def test_zero_gain_grades_are_omitted():
    gen = TelegramReportGenerator()
    block = gen.category_block(
        roman_numeral="I.",
        title="T",
        today_grades={
            "A": Counters(total=0),
            "B": Counters(total=2, female=1),
            "C": Counters(),
        },
        cumulative=Counters(total=9),
    )
    assert len(block.grade_lines) == 2  # one line + one pp/kp line, for B only
    assert "-និទ្ទេស B" in block.grade_lines[0]
    assert "A" not in "\n".join(block.grade_lines)


def test_grades_render_in_a_to_e_order_regardless_of_input_order():
    gen = TelegramReportGenerator()
    block = gen.category_block(
        roman_numeral="I.",
        title="T",
        today_grades={
            "E": Counters(total=5),
            "A": Counters(total=1),
            "C": Counters(total=3),
        },
        cumulative=Counters(total=9),
    )
    letters = [line.split()[1] for line in block.grade_lines if line.startswith("-")]
    assert letters == ["A", "C", "E"]


def test_grade_lines_can_be_suppressed_entirely():
    gen = TelegramReportGenerator(include_today_grades=False)
    block = gen.category_block(
        roman_numeral="I.",
        title="T",
        today_grades={"A": Counters(total=5)},
        cumulative=Counters(total=5),
    )
    assert block.grade_lines == []


def test_grade_filter_keeps_only_selected_grade_lines_and_labels_the_header():
    gen = TelegramReportGenerator(all_grades=("D",))
    text = gen.render(report_date=REPORT_DATE, categories=CATEGORIES)
    assert text.startswith("29/09/2026\nនិទ្ទេស : D\n")
    assert "-និទ្ទេស D" in text
    assert "-និទ្ទេស A" not in text


def test_unfiltered_report_has_no_grade_header():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert "និទ្ទេស : " not in text


def test_normalize_grades_orders_dedupes_and_defaults_to_all():
    from app.services.telegram_service import normalize_grades

    assert normalize_grades(["d", "A", "D"]) == ("A", "D")
    assert normalize_grades([]) == ("A", "B", "C", "D", "E")
    assert normalize_grades(None) == ("A", "B", "C", "D", "E")
    assert normalize_grades(["Z"]) == ("A", "B", "C", "D", "E")


# ------------------------------------------------------------------- message
def test_render_starts_with_the_dmy_date():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert text.startswith("29/09/2026\n")


def test_render_places_every_category_in_roman_order():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026" in text
    assert "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026" in text
    assert "III. បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង" in text
    assert text.index("I. ") < text.index("II. ") < text.index("III. ")


def test_full_message_matches_the_required_layout():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    expected = (
        "29/09/2026\n"
        "\n"
        "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
        "-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់\n"
        "(PP: 01 នាក់ , KP: 00 នាក់)\n"
        "សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់\n"
        "(PP: 08 នាក់, KP: 04 នាក់)\n"
        "\n"
        "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026\n"
        "-និទ្ទេស A ចំនួន : 03 នាក់ ស្រី 02 នាក់\n"
        "(PP: 00 នាក់ , KP: 01 នាក់)\n"
        "សរុបរួមចំនួន : 07 នាក់ ស្រី 04 នាក់\n"
        "(PP: 02 នាក់, KP: 01 នាក់)\n"
        "\n"
        "III. បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង\n"
        "សរុបរួមចំនួន : 00 នាក់ ស្រី 00 នាក់\n"
        "(PP: 00 នាក់, KP: 00 នាក់)\n"
    )
    assert text == expected


def test_grade_lines_use_today_while_total_line_uses_cumulative():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES[:1])
    assert "-និទ្ទេស D ចំនួន : 01" in text  # today's gain
    assert "សរុបរួមចំនួន : 12" in text  # cumulative


def test_empty_categories_can_be_hidden():
    text = build_report(
        report_date=REPORT_DATE, categories=CATEGORIES, include_empty_categories=False
    )
    assert "III." not in text
    assert "I. " in text and "II. " in text


def test_grand_total_block_is_opt_in():
    without = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert "GRAND TOTAL" not in without

    with_gt = build_report(
        report_date=REPORT_DATE,
        categories=CATEGORIES,
        include_grand_total=True,
        grand_total=Counters(total=19, female=9, pp=10, kp=5),
    )
    assert "GRAND TOTAL" in with_gt
    assert "សរុបរួមចំនួន : 19 នាក់ ស្រី 09 នាក់" in with_gt


def test_message_ends_with_a_single_newline():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_message_contains_no_trailing_whitespace_on_any_line():
    text = build_report(report_date=REPORT_DATE, categories=CATEGORIES)
    assert all(line == line.rstrip() for line in text.splitlines())
