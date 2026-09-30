"""
Cumulative engine.

Staff only ever enter *today's gain*.  Every cumulative figure in the system is
derived from that ledger:

    cumulative(category, as_of D)  =  SUM(today_* for every report with date <= D)
    cumulative(category, on   D)   =  cumulative(category, as_of D)
    new_total(D)                    =  previous_cumulative(D-1) + today's gain(D)

Editing or deleting a historical row therefore automatically re-bases every
later cumulative value, which is why the ledger is the single source of truth
and snapshots are treated purely as a derived cache.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import CATEGORY_ORDER
from app.models.reference import Category
from app.repositories.reference_repo import CategoryRepository
from app.repositories.report_repo import DailyReportRepository
from app.schemas.common import Counters

logger = logging.getLogger("scholar.cumulative")

GRADES: tuple[str, ...] = ("A", "B", "C", "D", "E")
ZERO = Counters()


@dataclass(slots=True)
class CategoryCumulative:
    """Cumulative snapshot for one category on one date."""

    category_id: str
    category_code: str
    report_date: date
    total: int = 0
    female: int = 0
    pp: int = 0
    kp: int = 0
    grade_total: dict[str, int] = field(default_factory=dict)
    grade_female: dict[str, int] = field(default_factory=dict)
    grade_pp: dict[str, int] = field(default_factory=dict)
    grade_kp: dict[str, int] = field(default_factory=dict)

    @property
    def male(self) -> int:
        return max(self.total - self.female, 0)

    def counters(self) -> Counters:
        return Counters(total=self.total, female=self.female, pp=self.pp, kp=self.kp)

    def grade_counters(self, grade: str) -> Counters:
        return Counters(
            total=self.grade_total.get(grade, 0),
            female=self.grade_female.get(grade, 0),
            pp=self.grade_pp.get(grade, 0),
            kp=self.grade_kp.get(grade, 0),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "total": self.total,
            "female": self.female,
            "pp": self.pp,
            "kp": self.kp,
            "grades": {
                grade: {
                    "total": self.grade_total.get(grade, 0),
                    "female": self.grade_female.get(grade, 0),
                    "pp": self.grade_pp.get(grade, 0),
                    "kp": self.grade_kp.get(grade, 0),
                }
                for grade in GRADES
            },
        }


class CumulativeService:
    """Computes and persists cumulative totals."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DailyReportRepository(session)
        self.category_repo = CategoryRepository(session)

    # ------------------------------------------------------------- querying
    async def cumulative_as_of(
        self, as_of: date, *, category_ids: list[str] | None = None
    ) -> dict[str, int]:
        return await self.repo.cumulative_as_of(
            as_of, category_ids=[c for c in category_ids or [] if c] or None
        )

    async def cumulative_by_category(self, as_of: date) -> list[CategoryCumulative]:
        categories = await self._active_categories()
        if not categories:
            return []
        totals = await self.repo.cumulative_by_category_as_of(as_of)
        grade_map: dict[str, dict[str, dict[str, int]]] = {}
        for category in categories:
            grade_map[category.code] = await self.repo.cumulative_grades_as_of(as_of, category.id)

        results: list[CategoryCumulative] = []
        for category in categories:
            raw = totals.get(category.id, {"total": 0, "female": 0, "pp": 0, "kp": 0})
            grades = grade_map.get(category.code, {})
            results.append(
                CategoryCumulative(
                    category_id=str(category.id),
                    category_code=category.code,
                    report_date=as_of,
                    total=raw["total"],
                    female=raw["female"],
                    pp=raw["pp"],
                    kp=raw["kp"],
                    grade_total={g: grades.get(g, {}).get("total", 0) for g in GRADES},
                    grade_female={g: grades.get(g, {}).get("female", 0) for g in GRADES},
                    grade_pp={g: grades.get(g, {}).get("pp", 0) for g in GRADES},
                    grade_kp={g: grades.get(g, {}).get("kp", 0) for g in GRADES},
                )
            )
        return results

    async def cumulative_for_category(self, as_of: date, category_id: str) -> CategoryCumulative:
        items = await self.cumulative_by_category(as_of)
        for item in items:
            if item.category_id == str(category_id):
                return item
        return CategoryCumulative(category_id=category_id, category_code="", report_date=as_of)

    async def previous_day_cumulative(
        self, as_of: date, category_id: str
    ) -> CategoryCumulative:
        """Cumulative carried into ``as_of`` from the day before."""
        return await self.cumulative_for_category(as_of - timedelta(days=1), category_id)

    async def grand_total(self, as_of: date) -> Counters:
        return Counters(**await self.repo.cumulative_as_of(as_of))

    async def period_totals(self, start: date, end: date, category_ids=None) -> Counters:
        return Counters(**await self.repo.totals_between(start, end, category_ids=category_ids))

    async def cumulative_series(
        self, start: date, end: date, *, category_ids: list | None = None
    ) -> list[dict[str, object]]:
        """
        Cumulative values for every day in ``[start, end]`` (days with no entry
        carry the previous day's value forward). ``category_ids`` narrows both
        the running total and the daily gains to those categories.
        """
        daily = await self.repo.daily_series(start, end, category_ids=category_ids)
        by_date = {row["date"]: row for row in daily}
        running = Counters()
        prior = await self.repo.cumulative_as_of(start - timedelta(days=1), category_ids=category_ids)
        running = Counters(**prior)
        series: list[dict[str, object]] = []
        cursor = start
        while cursor <= end:
            row = by_date.get(cursor)
            if row:
                running = Counters(
                    total=running.total + row["total"],
                    female=running.female + row["female"],
                    pp=running.pp + row["pp"],
                    kp=running.kp + row["kp"],
                )
            series.append(
                {
                    "date": cursor,
                    "total": running.total,
                    "female": running.female,
                    "male": max(running.total - running.female, 0),
                    "pp": running.pp,
                    "kp": running.kp,
                    # That day's own gain (0 when nothing was recorded), so
                    # clients never have to diff running totals.
                    "gain": {
                        "total": row["total"] if row else 0,
                        "female": row["female"] if row else 0,
                        "pp": row["pp"] if row else 0,
                        "kp": row["kp"] if row else 0,
                    },
                }
            )
            cursor += timedelta(days=1)
        return series

    # ----------------------------------------------------------- persistence
    async def recompute_from(self, affected_date: date) -> int:
        """
        Rebuild the snapshot series for ``affected_date`` and every later date
        that has a report.  Returns the number of snapshot rows written.
        """
        later_dates = await self._dates_from(affected_date)
        if not later_dates:
            await self.repo.delete_snapshots_from(affected_date)
            return 0

        categories = await self._active_categories()
        if not categories:
            return 0

        # Running ledger: cumulative before the first recomputed date.
        base_totals = await self.repo.cumulative_as_of(affected_date - timedelta(days=1))
        running = {str(c.id): Counters(**base_totals) for c in categories}
        grade_running = {str(c.id): await self.repo.cumulative_grades_as_of(
            affected_date - timedelta(days=1), c.id) for c in categories}

        written = 0
        for day in later_dates:
            rows = await self.repo.totals_between(day, day)
            per_category = await self.repo.by_category_totals(day, day)
            per_category_grades = {
                str(c.id): await self.repo.cumulative_grades_as_of(day, c.id) for c in categories
            }
            for category in categories:
                key = str(category.id)
                gain = per_category.get(category.id, {"total": 0, "female": 0, "pp": 0, "kp": 0})
                current = running[key]
                running[key] = Counters(
                    total=current.total + gain["total"],
                    female=current.female + gain["female"],
                    pp=current.pp + gain["pp"],
                    kp=current.kp + gain["kp"],
                )
                grades = per_category_grades[key]
                grade_cumulative = {
                    grade: {
                        "total": int(grades.get(grade, {}).get("total", 0)),
                        "female": int(grades.get(grade, {}).get("female", 0)),
                        "pp": int(grades.get(grade, {}).get("pp", 0)),
                        "kp": int(grades.get(grade, {}).get("kp", 0)),
                    }
                    for grade in GRADES
                }
                cumulative = running[key]
                await self.repo.replace_snapshot(
                    day,
                    category.id,
                    {
                        "cumulative_total": cumulative.total,
                        "cumulative_female": cumulative.female,
                        "cumulative_pp": cumulative.pp,
                        "cumulative_kp": cumulative.kp,
                        "grade_cumulative": grade_cumulative,
                    },
                )
                written += 1
            grade_running = per_category_grades
            _ = rows  # totals for the day (all categories) retained for debugging
        await self.session.flush()
        logger.info("Recomputed %s cumulative snapshots from %s", written, affected_date)
        return written

    async def recompute_all(self) -> int:
        first = await self.repo.first_date()
        if first is None:
            return 0
        await self.repo.delete_snapshots_from(first)
        return await self.recompute_from(first)

    async def snapshot_for(self, report_date: date) -> dict[str, Counters]:
        """Cumulative per category code on ``report_date`` (from the cache)."""
        snapshots = await self.repo.snapshots_between(report_date, report_date)
        categories = {str(c.id): c for c in await self._active_categories()}
        return {
            categories[s.category_id].code: Counters(
                total=s.cumulative_total,
                female=s.cumulative_female,
                pp=s.cumulative_pp,
                kp=s.cumulative_kp,
            )
            for s in snapshots
            if str(s.category_id) in categories
        }

    # -------------------------------------------------------------- helpers
    async def _active_categories(self) -> list[Category]:
        categories = await self.category_repo.list_ordered(active_only=True)
        if not categories:  # fall back to inactive rows so reports still resolve
            categories = await self.category_repo.list_ordered(active_only=False)
        return sorted(categories, key=lambda c: c.position)

    async def _dates_from(self, start: date) -> list[date]:
        from sqlalchemy import distinct, select

        from app.models.report import DailyReport

        stmt = (
            select(distinct(DailyReport.report_date))
            .where(DailyReport.report_date >= start)
            .order_by(DailyReport.report_date.asc())
        )
        return list((await self.session.scalars(stmt)).all())

    @staticmethod
    def order_categories(codes: list[str]) -> list[str]:
        return [c for c in CATEGORY_ORDER if c in codes] + [
            c for c in codes if c not in CATEGORY_ORDER
        ]
