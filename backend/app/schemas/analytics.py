"""Dashboard, statistics, export and Telegram schemas."""

from __future__ import annotations

from datetime import date as Date

from pydantic import Field

from app.schemas.common import Counters, SchemaBase


class CategoryMetric(SchemaBase):
    category_id: str
    category_code: str
    title: str
    roman_numeral: str
    position: int
    today: Counters = Field(default_factory=Counters)
    month: Counters = Field(default_factory=Counters)
    year: Counters = Field(default_factory=Counters)
    cumulative: Counters = Field(default_factory=Counters)
    cumulative_grades: dict[str, Counters] = Field(default_factory=dict)
    male_today: int = 0
    male_month: int = 0
    male_year: int = 0


class GradeDistributionItem(SchemaBase):
    grade: str
    today: int = 0
    month: int = 0
    year: int = 0
    cumulative: int = 0
    female: int = 0
    pp: int = 0
    kp: int = 0


class GenderDistribution(SchemaBase):
    male: int = 0
    female: int = 0
    male_pct: float = 0.0
    female_pct: float = 0.0


class ProvinceDistribution(SchemaBase):
    pp: int = 0
    kp: int = 0
    pp_pct: float = 0.0
    kp_pct: float = 0.0


class ChartPoint(SchemaBase):
    date: Date
    total: int = 0
    female: int = 0
    male: int = 0
    pp: int = 0
    kp: int = 0


class MonthlyPoint(SchemaBase):
    month: str
    period: str
    total: int = 0
    female: int = 0
    male: int = 0
    pp: int = 0
    kp: int = 0
    active_days: int = 0


class ActivityItem(SchemaBase):
    id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str | None = None
    user_email: str | None = None
    created_at: str | None = None


class CategoryCompletion(SchemaBase):
    category_code: str
    title: str
    submitted: bool = False
    today_total: int = 0


class DashboardResponse(SchemaBase):
    generated_for: Date
    current_year: int
    headline: Counters = Field(default_factory=Counters)
    today: Counters = Field(default_factory=Counters)
    month: Counters = Field(default_factory=Counters)
    year: Counters = Field(default_factory=Counters)
    categories: list[CategoryMetric] = Field(default_factory=list)
    grade_distribution: list[GradeDistributionItem] = Field(default_factory=list)
    gender: GenderDistribution = Field(default_factory=GenderDistribution)
    provinces: ProvinceDistribution = Field(default_factory=ProvinceDistribution)
    province_distribution: list[CategoryMetric] = Field(default_factory=list)
    daily_trend: list[ChartPoint] = Field(default_factory=list)
    monthly_trend: list[MonthlyPoint] = Field(default_factory=list)
    recent_activities: list[ActivityItem] = Field(default_factory=list)
    has_report_today: bool = False
    report_completion: list[CategoryCompletion] = Field(default_factory=list)


class StatisticsResponse(SchemaBase):
    current_year: int
    period_start: Date
    period_end: Date
    by_category: list[CategoryMetric] = Field(default_factory=list)
    by_grade: list[GradeDistributionItem] = Field(default_factory=list)
    by_month: list[MonthlyPoint] = Field(default_factory=list)
    by_day_of_week: dict[str, int] = Field(default_factory=dict)
    best_day: ChartPoint | None = None
    averages: dict[str, float] = Field(default_factory=dict)
    gender: GenderDistribution = Field(default_factory=GenderDistribution)


class SummaryResponse(SchemaBase):
    scope: str
    period_start: Date
    period_end: Date
    current_year: int
    totals: Counters
    by_category: list[CategoryMetric] = Field(default_factory=list)
    by_grade: list[GradeDistributionItem] = Field(default_factory=list)
    text: str


class TelegramMessage(SchemaBase):
    report_date: Date | None = None
    include_today_grades: bool = True
    include_grand_total: bool = False
    include_empty_categories: bool = True
    zero_pad: bool = True
    text: str
    message_id: int | None = None
    sent: bool = False


class TelegramSendRequest(SchemaBase):
    report_date: Date
    chat_id: str | None = Field(default=None, max_length=64)
    include_today_grades: bool = True
    include_grand_total: bool = False
    include_empty_categories: bool = True
    zero_pad: bool = True
    grades: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Only report these grades (A-E); empty means all.",
    )
    dry_run: bool = Field(default=False, description="Preview without sending.")


class ExportRequest(SchemaBase):
    report_date: Date | None = None
    start_date: Date | None = None
    end_date: Date | None = None
    category_ids: list[str] = Field(default_factory=list)
    format: str = Field(default="csv", pattern="^(csv|excel|pdf)$")
    include_grade_breakdown: bool = True
    include_cumulative: bool = True
    zero_pad: bool = False
    title: str | None = None
