"""Dashboard, statistics and trend aggregation for the admin UI."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import local_today, month_bounds, year_bounds
from app.models.user import User
from app.repositories.audit_repo import AuditRepository
from app.repositories.reference_repo import CategoryRepository
from app.repositories.report_repo import DailyReportRepository
from app.schemas.analytics import (
    ActivityItem,
    CategoryCompletion,
    CategoryMetric,
    ChartPoint,
    DashboardResponse,
    GenderDistribution,
    GradeDistributionItem,
    MonthlyPoint,
    ProvinceDistribution,
    StatisticsResponse,
)
from app.schemas.common import Counters
from app.services.cumulative_service import GRADES, CumulativeService
from app.services.settings_service import SettingsService

logger = logging.getLogger("scholar.dashboard")

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _to_chart_points(rows: list[dict]) -> list[ChartPoint]:
    return [
        ChartPoint(
            date=row["date"],
            total=row.get("total", 0),
            female=row.get("female", 0),
            male=max(row.get("total", 0) - row.get("female", 0), 0),
            pp=row.get("pp", 0),
            kp=row.get("kp", 0),
        )
        for row in rows
    ]


def _male(counts: Counters) -> int:
    return max(counts.total - counts.female, 0)


def _gender(counts: Counters) -> GenderDistribution:
    total = counts.total
    male = _male(counts)
    pct = (male / total * 100) if total else 0.0
    return GenderDistribution(
        male=male,
        female=counts.female,
        male_pct=round(pct if total else 0.0, 2),
        female_pct=round(100 - pct if total else 0.0, 2),
    )


def _provinces(counts: Counters) -> ProvinceDistribution:
    total = counts.total
    return ProvinceDistribution(
        pp=counts.pp,
        kp=counts.kp,
        pp_pct=round(counts.pp / total * 100, 2) if total else 0.0,
        kp_pct=round(counts.kp / total * 100, 2) if total else 0.0,
    )


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DailyReportRepository(session)
        self.category_repo = CategoryRepository(session)
        self.audit_repo = AuditRepository(session)
        self.cumulative = CumulativeService(session)
        self.settings = SettingsService(session)

    # ------------------------------------------------------------ dashboard
    async def dashboard(
        self,
        *,
        reference_date: date | None = None,
        trend_days: int = 30,
        trend_months: int = 12,
    ) -> DashboardResponse:
        today = reference_date or local_today()
        year = await self.settings.get_current_year()
        categories = await self.category_repo.list_ordered()
        month_start, month_end = month_bounds(today)
        year_start, year_end = year_bounds(today)

        by_category_today = await self.repo.by_category_totals(today, today)
        by_category_month = await self.repo.by_category_totals(month_start, month_end)
        by_category_year = await self.repo.by_category_totals(year_start, year_end)
        cumulative_by_category = await self.cumulative.cumulative_by_category(today)

        category_metrics: list[CategoryMetric] = []
        for category in categories:
            t = _counters(by_category_today.get(category.id))
            m = _counters(by_category_month.get(category.id))
            y = _counters(by_category_year.get(category.id))
            cum = next(
                (c for c in cumulative_by_category if c.category_id == str(category.id)), None
            )
            cumulative_counts = cum.counters() if cum else Counters()
            cumulative_grades = {g: cum.grade_counters(g) for g in GRADES} if cum else {}
            category_metrics.append(
                CategoryMetric(
                    category_id=str(category.id),
                    category_code=category.code,
                    title=category.render_title(year),
                    roman_numeral=category.roman_numeral,
                    position=category.position,
                    today=t,
                    month=m,
                    year=y,
                    cumulative=cumulative_counts,
                    cumulative_grades=cumulative_grades,
                    male_today=_male(t),
                    male_month=_male(m),
                    male_year=_male(y),
                )
            )

        today_total = sum(m.today.total for m in category_metrics)
        today_female = sum(m.today.female for m in category_metrics)
        month_counts = _sum_counters([m.month for m in category_metrics])
        year_counts = _sum_counters([m.year for m in category_metrics])
        headline = _sum_counters([m.cumulative for m in category_metrics])

        grade_today = await self.repo.grade_totals_between(today, today)
        grade_month = await self.repo.grade_totals_between(month_start, month_end)
        grade_year = await self.repo.grade_totals_between(year_start, year_end)
        grade_cumulative = {
            m.category_code: m for m in await self.cumulative.cumulative_by_category(today)
        }
        merged_grades = _merge_grade_cumulative(grade_cumulative)
        grade_distribution = [
            GradeDistributionItem(
                grade=grade,
                today=grade_today.get(grade, {}).get("total", 0),
                month=grade_month.get(grade, {}).get("total", 0),
                year=grade_year.get(grade, {}).get("total", 0),
                cumulative=merged_grades.get(grade, {}).get("total", 0),
                female=merged_grades.get(grade, {}).get("female", 0),
                pp=merged_grades.get(grade, {}).get("pp", 0),
                kp=merged_grades.get(grade, {}).get("kp", 0),
            )
            for grade in GRADES
        ]

        trend_start = max(today - timedelta(days=trend_days - 1), year_start)
        daily_trend = _to_chart_points(await self.repo.daily_series(trend_start, today))

        monthly_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        monthly_start = max(monthly_start, date(monthly_start.year - trend_months // 12, 1, 1))
        monthly_rows = await self.repo.monthly_series(monthly_start, today)
        monthly_trend = [
            MonthlyPoint(
                month=_month_label(row["period"]),
                period=row["period"],
                total=row["total"],
                female=row["female"],
                male=max(row["total"] - row["female"], 0),
                pp=row["pp"],
                kp=row["kp"],
                active_days=row["active_days"],
            )
            for row in monthly_rows
        ]

        completion = []
        for metric in category_metrics:
            completion.append(
                CategoryCompletion(
                    category_code=metric.category_code,
                    title=metric.title,
                    submitted=metric.today.total > 0 or bool(by_category_today.get(
                        next(c.id for c in categories if c.code == metric.category_code)
                    )),
                    today_total=metric.today.total,
                )
            )

        activities = [
            ActivityItem(
                id=str(log.id),
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                summary=log.summary,
                user_email=log.user_email,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in await self.audit_repo.recent(limit=10)
        ]

        return DashboardResponse(
            generated_for=today,
            current_year=year,
            headline=headline,
            today=Counters(total=today_total, female=today_female,
                           pp=sum(m.today.pp for m in category_metrics),
                           kp=sum(m.today.kp for m in category_metrics)),
            month=month_counts,
            year=year_counts,
            categories=category_metrics,
            grade_distribution=grade_distribution,
            gender=_gender(headline),
            provinces=_provinces(headline),
            province_distribution=list(category_metrics),
            daily_trend=daily_trend,
            monthly_trend=monthly_trend,
            recent_activities=activities,
            has_report_today=bool(by_category_today),
            report_completion=completion,
        )

    # ---------------------------------------------------------- statistics
    async def statistics(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        category_id: UUID | None = None,
    ) -> StatisticsResponse:
        today = local_today()
        end = end or today
        start = start or date(end.year, 1, 1)
        if end < start:
            start, end = end, start
        year = await self.settings.get_current_year()

        category_ids = [category_id] if category_id else None
        categories = await self.category_repo.list_ordered()
        by_category = await self.repo.by_category_totals(start, end)
        totals = await self.repo.totals_between(start, end, category_ids=category_ids)
        grades = await self.repo.grade_totals_between(start, end, category_ids=category_ids)

        category_metrics = [
            CategoryMetric(
                category_id=str(c.id),
                category_code=c.code,
                title=c.render_title(year),
                roman_numeral=c.roman_numeral,
                position=c.position,
                month=_counters(by_category.get(c.id)),
                male_month=_male(_counters(by_category.get(c.id))),
            )
            for c in categories
        ]

        daily = await self.repo.daily_series(start, end, category_ids=category_ids)
        monthly_rows = await self.repo.monthly_series(start, end, category_ids=category_ids)
        weekdays = await self.repo.weekdays(start, end)
        active_days = len(daily) or 0
        grand = _counters(totals)

        best_day = None
        if daily:
            top = max(daily, key=lambda r: r["total"])
            best_day = ChartPoint(
                date=top["date"],
                total=top["total"],
                female=top["female"],
                male=max(top["total"] - top["female"], 0),
                pp=top["pp"],
                kp=top["kp"],
            )

        return StatisticsResponse(
            current_year=year,
            period_start=start,
            period_end=end,
            by_category=category_metrics,
            by_grade=[
                GradeDistributionItem(
                    grade=grade,
                    total=grades.get(grade, {}).get("total", 0),
                    female=grades.get(grade, {}).get("female", 0),
                    pp=grades.get(grade, {}).get("pp", 0),
                    kp=grades.get(grade, {}).get("kp", 0),
                )
                for grade in GRADES
            ],
            by_month=[
                MonthlyPoint(
                    month=_month_label(row["period"]),
                    period=row["period"],
                    total=row["total"],
                    female=row["female"],
                    male=max(row["total"] - row["female"], 0),
                    pp=row["pp"],
                    kp=row["kp"],
                    active_days=row["active_days"],
                )
                for row in monthly_rows
            ],
            by_day_of_week={day: weekdays.get(day, 0) for day in WEEKDAY_ORDER if day in weekdays},
            best_day=best_day,
            averages={
                "per_active_day": round(grand.total / active_days, 2) if active_days else 0.0,
                "per_calendar_day": round(grand.total / max((end - start).days + 1, 1), 2),
                "female_share": round(grand.female / grand.total * 100, 2) if grand.total else 0.0,
                "pp_share": round(grand.pp / grand.total * 100, 2) if grand.total else 0.0,
                "kp_share": round(grand.kp / grand.total * 100, 2) if grand.total else 0.0,
                "active_days": float(active_days),
            },
            gender=_gender(grand),
        )

    # ------------------------------------------------------------ utilities
    async def category_overview(self, reference_date: date | None = None) -> list[CategoryMetric]:
        today = reference_date or local_today()
        year = await self.settings.get_current_year()
        cumulative = await self.cumulative.cumulative_by_category(today)
        month_start, month_end = month_bounds(today)
        by_month = await self.repo.by_category_totals(month_start, month_end)
        by_today = await self.repo.by_category_totals(today, today)
        out: list[CategoryMetric] = []
        for category in await self.category_repo.list_ordered():
            cum = next((c for c in cumulative if c.category_id == str(category.id)), None)
            out.append(
                CategoryMetric(
                    category_id=str(category.id),
                    category_code=category.code,
                    title=category.render_title(year),
                    roman_numeral=category.roman_numeral,
                    position=category.position,
                    today=_counters(by_today.get(category.id)),
                    month=_counters(by_month.get(category.id)),
                    cumulative=cum.counters() if cum else Counters(),
                )
            )
        return out

    async def available_dates(self) -> list[str]:
        return [d.isoformat() for d in await self.repo.list_dates()]


def _counters(raw: dict | None) -> Counters:
    if not raw:
        return Counters()
    return Counters(
        total=int(raw.get("total", 0)),
        female=int(raw.get("female", 0)),
        pp=int(raw.get("pp", 0)),
        kp=int(raw.get("kp", 0)),
    )


def _sum_counters(items: list[Counters]) -> Counters:
    return Counters(
        total=sum(i.total for i in items),
        female=sum(i.female for i in items),
        pp=sum(i.pp for i in items),
        kp=sum(i.kp for i in items),
    )


def _merge_grade_cumulative(
    per_category: dict[str, object],
) -> dict[str, dict[str, int]]:
    merged: dict[str, dict[str, int]] = {
        grade: {"total": 0, "female": 0, "pp": 0, "kp": 0} for grade in GRADES
    }
    for item in per_category.values():
        for grade in GRADES:
            counters = item.grade_counters(grade)  # type: ignore[attr-defined]
            merged[grade]["total"] += counters.total
            merged[grade]["female"] += counters.female
            merged[grade]["pp"] += counters.pp
            merged[grade]["kp"] += counters.kp
    return merged


def _month_label(period: str) -> str:
    try:
        year, month = period.split("-")
        return f"{year}-{month}"
    except (AttributeError, ValueError):
        return period
