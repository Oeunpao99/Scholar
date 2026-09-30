"""
Khmer Telegram report generator.

Produces the exact message layout required by the ministry:

    29/09/2026

    I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026
    -និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់
    (PP: 01 នាក់ , KP: 00 នាក់)
    សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់
    (PP: 08 នាក់, KP: 04 នាក់)

Rules enforced here:
  * the per-grade line shows ONLY today's gain for that grade;
  * the ``សរុបរួមចំនួន`` line shows the CUMULATIVE total;
  * every number is rendered with two digits (``01``, ``00``, ``09``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.core.pagination import format_date_dmy, format_number
from app.schemas.common import Counters

# ---------------------------------------------------------------- Khmer copy
GRADE_LINE_PREFIX = "-និទ្ទេស"
GRADE_COUNT_LABEL = "ចំនួន"
TOTAL_LABEL = "សរុបរួមចំនួន"
PERSON = "នាក់"
FEMALE = "ស្រី"
PP_LABEL = "PP"
KP_LABEL = "KP"
COLON = " : "
GRAND_TOTAL_TITLE = "GRAND TOTAL"
GRADE_FILTER_LABEL = "និទ្ទេស"

DEFAULT_GRADES: tuple[str, ...] = ("A", "B", "C", "D", "E")


@dataclass(slots=True)
class TelegramCategoryBlock:
    """Rendered block for one category."""

    roman_numeral: str
    title: str
    grade_lines: list[str]
    total_line: str
    pp_kp_line: str
    cumulative: Counters

    def render(self) -> str:
        parts = [f"{self.roman_numeral} {self.title}", *self.grade_lines, self.total_line, self.pp_kp_line]
        return "\n".join(parts)


class TelegramReportGenerator:
    """Stateless formatter - feed it data, get the exact message text."""

    def __init__(
        self,
        *,
        zero_pad: bool = True,
        include_today_grades: bool = True,
        include_grand_total: bool = False,
        include_empty_categories: bool = True,
        all_grades: tuple[str, ...] = DEFAULT_GRADES,
    ) -> None:
        self.zero_pad = zero_pad
        self.include_today_grades = include_today_grades
        self.include_grand_total = include_grand_total
        self.include_empty_categories = include_empty_categories
        self.all_grades = all_grades

    @property
    def is_grade_filtered(self) -> bool:
        return set(self.all_grades) != set(DEFAULT_GRADES)

    # --------------------------------------------------------------- numbers
    def num(self, value: int | float) -> str:
        """Two-digit zero-padded number, as mandated by the report format."""
        return format_number(value) if self.zero_pad else str(int(value))

    # ----------------------------------------------------------------- parts
    def grade_line(self, grade: str, gain: Counters) -> str:
        """``-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់`` - today's gain only."""
        return (
            f"{GRADE_LINE_PREFIX} {grade} {GRADE_COUNT_LABEL}{COLON}"
            f"{self.num(gain.total)} {PERSON} {FEMALE} {self.num(gain.female)} {PERSON}"
        )

    def grade_pp_kp_line(self, gain: Counters) -> str:
        """``(PP: 01 នាក់ , KP: 00 នាក់)`` - note the space before the comma."""
        return f"({PP_LABEL}: {self.num(gain.pp)} {PERSON} , {KP_LABEL}: {self.num(gain.kp)} {PERSON})"

    def total_line(self, cumulative: Counters) -> str:
        """``សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់`` - cumulative figures."""
        return (
            f"{TOTAL_LABEL}{COLON}"
            f"{self.num(cumulative.total)} {PERSON} {FEMALE} {self.num(cumulative.female)} {PERSON}"
        )

    def total_pp_kp_line(self, cumulative: Counters) -> str:
        """``(PP: 08 នាក់, KP: 04 នាក់)`` - no space before the comma here."""
        return f"({PP_LABEL}: {self.num(cumulative.pp)} {PERSON}, {KP_LABEL}: {self.num(cumulative.kp)} {PERSON})"

    # ---------------------------------------------------------------- blocks
    def category_block(
        self,
        *,
        roman_numeral: str,
        title: str,
        today_grades: dict[str, Counters],
        cumulative: Counters,
    ) -> TelegramCategoryBlock:
        grade_lines: list[str] = []
        if self.include_today_grades:
            for grade in self.all_grades:
                gain = today_grades.get(grade)
                if gain is None or gain.is_zero():
                    continue
                grade_lines.append(self.grade_line(grade, gain))
                grade_lines.append(self.grade_pp_kp_line(gain))

        return TelegramCategoryBlock(
            roman_numeral=roman_numeral,
            title=title,
            grade_lines=grade_lines,
            total_line=self.total_line(cumulative),
            pp_kp_line=self.total_pp_kp_line(cumulative),
            cumulative=cumulative,
        )

    def grand_total_block(self, cumulative: Counters) -> str:
        return "\n".join(
            [GRAND_TOTAL_TITLE, self.total_line(cumulative), self.total_pp_kp_line(cumulative)]
        )

    # ------------------------------------------------------------- rendering
    def render(
        self,
        *,
        report_date: date,
        categories: list[dict],
        grand_total: Counters | None = None,
    ) -> str:
        """
        ``categories`` items require ``roman_numeral``, ``title``,
        ``today_grades`` (grade -> Counters) and ``cumulative`` (Counters).
        """
        blocks: list[str] = []
        for item in categories:
            if not self.include_empty_categories and _is_empty(item):
                continue
            blocks.append(
                self.category_block(
                    roman_numeral=item["roman_numeral"],
                    title=item["title"],
                    today_grades=item.get("today_grades") or {},
                    cumulative=item.get("cumulative") or Counters(),
                ).render()
            )

        if self.include_grand_total and grand_total is not None:
            blocks.append(self.grand_total_block(grand_total))

        header = format_date_dmy(report_date)
        if self.is_grade_filtered:
            # Totals below only count these grades - say so up front.
            header += f"\n{GRADE_FILTER_LABEL}{COLON}{', '.join(self.all_grades)}"
        sections = [header, *blocks]
        return "\n\n".join(sections).strip() + "\n"

    def render_single_category(self, *, report_date: date, block: TelegramCategoryBlock) -> str:
        return f"{format_date_dmy(report_date)}\n\n{block.render()}\n"


def _is_empty(item: dict) -> bool:
    cumulative: Counters = item.get("cumulative") or Counters()
    gains: dict[str, Counters] = item.get("today_grades") or {}
    return cumulative.is_zero() and all(g.is_zero() for g in gains.values())


def build_report(
    *,
    report_date: date,
    categories: list[dict],
    zero_pad: bool = True,
    include_today_grades: bool = True,
    include_grand_total: bool = False,
    include_empty_categories: bool = True,
    grand_total: Counters | None = None,
) -> str:
    """Convenience wrapper around :class:`TelegramReportGenerator`."""
    return TelegramReportGenerator(
        zero_pad=zero_pad,
        include_today_grades=include_today_grades,
        include_grand_total=include_grand_total,
        include_empty_categories=include_empty_categories,
    ).render(report_date=report_date, categories=categories, grand_total=grand_total)
