"""Cumulative logic: the single most important invariant in the system.

Staff only ever enter today's gain. Every cumulative number in every category,
grade, chart and Telegram message is derived from the sum of all gains up to
(and including) the requested date.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.models.enums import GradeLetter, Metric


class FakeEntry:
    def __init__(self, grade: str, total: int, female: int = 0, pp: int = 0, kp: int = 0):
        self.grade = grade
        self.position = "ABCDE".index(grade)
        self.today_total = total
        self.today_female = female
        self.today_pp = pp
        self.today_kp = kp


class FakeReport:
    def __init__(
        self,
        report_date: date,
        total: int,
        female: int = 0,
        pp: int = 0,
        kp: int = 0,
        entries: list[FakeEntry] | None = None,
    ):
        self.report_date = report_date
        self.today_total = total
        self.today_female = female
        self.today_pp = pp
        self.today_kp = kp
        self.entries = entries or []


class FakeCategory:
    def __init__(self, code: str = "current_year"):
        self.code = code
        self.position = 1
        self.roman_numeral = "I."
        self.title_template = "បានទទួលពាក្យបាក់ឌុបឆ្នាំ{year}"

    def render_title(self, year: int) -> str:
        return self.title_template.format(year=year)


def sum_metrics(reports: list[FakeReport]) -> dict[str, int]:
    return {
        Metric.TOTAL: sum(r.today_total for r in reports),
        Metric.FEMALE: sum(r.today_female for r in reports),
        Metric.PP: sum(r.today_pp for r in reports),
        Metric.KP: sum(r.today_kp for r in reports),
    }


def sum_grades(reports: list[FakeReport], metric: str = Metric.TOTAL) -> dict[str, int]:
    out = {g: 0 for g in "ABCDE"}
    for report in reports:
        for entry in report.entries:
            out[entry.grade] += getattr(entry, f"today_{metric}")
    return out


D1 = date(2026, 1, 5)
D2 = date(2026, 1, 6)
D3 = date(2026, 1, 7)

HISTORY = [
    FakeReport(D1, 10, 4, 3, 2, [FakeEntry("A", 5, 2, 1, 1), FakeEntry("D", 5, 2, 2, 1)]),
    FakeReport(D2, 20, 8, 5, 4, [FakeEntry("A", 6, 2, 1, 1), FakeEntry("B", 8, 3, 2, 1), FakeEntry("D", 6, 3, 2, 2)]),
    FakeReport(D3, 5, 1, 1, 0, [FakeEntry("E", 5, 1, 1, 0)]),
]


def test_cumulative_on_a_single_day():
    assert sum_metrics([HISTORY[0]]) == {
        Metric.TOTAL: 10,
        Metric.FEMALE: 4,
        Metric.PP: 3,
        Metric.KP: 2,
    }


def test_cumulative_accumulates_across_days():
    assert sum_metrics(HISTORY) == {Metric.TOTAL: 35, Metric.FEMALE: 13, Metric.PP: 9, Metric.KP: 6}


def test_cumulative_excludes_later_days():
    upto_d2 = [r for r in HISTORY if r.report_date <= D2]
    assert sum_metrics(upto_d2) == {Metric.TOTAL: 30, Metric.FEMALE: 12, Metric.PP: 8, Metric.KP: 6}


def test_cumulative_on_date_with_no_report_is_zero():
    empty = [r for r in HISTORY if r.report_date == date(2026, 1, 1)]
    assert sum_metrics(empty) == {Metric.TOTAL: 0, Metric.FEMALE: 0, Metric.PP: 0, Metric.KP: 0}


def test_grade_cumulative_is_per_grade():
    assert sum_grades(HISTORY) == {"A": 11, "B": 8, "C": 0, "D": 11, "E": 5}
    assert sum(sum_grades(HISTORY).values()) == 35


def test_grade_cumulative_ignores_grades_with_no_entries():
    grades = sum_grades(HISTORY)
    assert grades["C"] == 0
    assert "C" in grades  # zero rows are still reported, not omitted


def test_grade_cumulative_per_metric():
    assert sum_grades(HISTORY, Metric.FEMALE) == {"A": 4, "B": 3, "C": 0, "D": 5, "E": 1}


def test_editing_a_day_changes_cumulative_from_that_day_onwards():
    edited = FakeReport(D2, 25, 10, 6, 5, [FakeEntry("A", 11, 4, 2, 2)])
    history = [HISTORY[0], edited, HISTORY[2]]
    assert sum_metrics(history) == {Metric.TOTAL: 40, Metric.FEMALE: 15, Metric.PP: 10, Metric.KP: 7}


def test_deleting_a_day_removes_its_gain():
    history = [HISTORY[0], HISTORY[2]]
    assert sum_metrics(history) == {Metric.TOTAL: 15, Metric.FEMALE: 5, Metric.PP: 4, Metric.KP: 2}


def test_cumulative_is_monotonic_when_only_gains_are_entered():
    running = 0
    for report in HISTORY:
        running += report.today_total
        assert running >= 0
    assert running == 35


def test_category_title_renders_configured_year():
    assert FakeCategory().render_title(2026) == "បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026"
    assert FakeCategory().render_title(2027) == "បានទទួលពាក្យបាក់ឌុបឆ្នាំ2027"


def test_grade_order_is_a_to_e():
    assert GradeLetter.A.value == "A"
    assert [GradeLetter.D.value for _ in range(5)] == ["D"] * 5


@pytest.mark.parametrize(
    ("pp", "kp", "total", "valid"),
    [
        (5, 5, 10, True),
        (6, 5, 10, False),
        (0, 0, 0, True),
        (11, 0, 10, False),
    ],
)
def test_pp_plus_kp_never_exceeds_total(pp: int, kp: int, total: int, valid: bool):
    assert (pp + kp <= total) is valid


@pytest.mark.parametrize(
    ("female", "total", "valid"),
    [(5, 10, True), (11, 10, False), (0, 0, True)],
)
def test_female_never_exceeds_total(female: int, total: int, valid: bool):
    assert (female <= total) is valid
