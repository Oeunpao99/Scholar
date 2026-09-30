"""Daily report, grade entry and snapshot data access (incl. aggregate queries)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import Select, String, and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.reference import Category
from app.models.report import DailyGradeEntry, DailyReport, DailyTotalsSnapshot
from app.repositories.base import BaseRepository

METRICS = ("today_total", "today_female", "today_pp", "today_kp")


def _sum_metrics(column_prefix: str = "today") -> tuple[Any, ...]:
    return tuple(func.coalesce(func.sum(getattr(DailyReport, f"{column_prefix}_{m}")), 0) for m in
                 ("total", "female", "pp", "kp"))


class DailyReportRepository(BaseRepository[DailyReport]):
    model = DailyReport

    # ------------------------------------------------------------- retrieval
    async def get_detailed(self, report_id: uuid.UUID) -> DailyReport | None:
        stmt = (
            select(DailyReport)
            .options(
                joinedload(DailyReport.category),
                joinedload(DailyReport.created_by_user),
                selectinload(DailyReport.entries),
            )
            .where(DailyReport.id == report_id)
        )
        return await self.first(stmt)

    async def get_for_date(self, report_date: date, category_id: uuid.UUID) -> DailyReport | None:
        stmt = (
            select(DailyReport)
            .options(joinedload(DailyReport.category), selectinload(DailyReport.entries))
            .where(DailyReport.report_date == report_date, DailyReport.category_id == category_id)
        )
        return await self.first(stmt)

    async def get_for_date_code(self, report_date: date, category_code: str) -> DailyReport | None:
        stmt = (
            select(DailyReport)
            .join(Category, DailyReport.category_id == Category.id)
            .options(joinedload(DailyReport.category), selectinload(DailyReport.entries))
            .where(DailyReport.report_date == report_date, Category.code == category_code)
        )
        return await self.first(stmt)

    async def list_by_date(
        self, report_date: date, *, active_only: bool = True
    ) -> list[DailyReport]:
        stmt = (
            select(DailyReport)
            .join(Category, DailyReport.category_id == Category.id)
            .options(joinedload(DailyReport.category), selectinload(DailyReport.entries))
            .where(DailyReport.report_date == report_date)
        )
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        stmt = stmt.order_by(Category.position.asc())
        return list((await self.session.scalars(stmt)).unique().all())

    async def list_in_range(
        self,
        start: date,
        end: date,
        *,
        category_ids: Sequence[uuid.UUID] | None = None,
    ) -> list[DailyReport]:
        stmt = (
            select(DailyReport)
            .join(Category, DailyReport.category_id == Category.id)
            .options(joinedload(DailyReport.category), selectinload(DailyReport.entries))
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
        )
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        stmt = stmt.order_by(DailyReport.report_date.asc(), Category.position.asc())
        return list((await self.session.scalars(stmt)).unique().all())

    async def paginate_filtered(
        self,
        stmt: Select,
        page: int,
        size: int,
    ) -> tuple[list[DailyReport], int]:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.offset((page - 1) * size).limit(size)
        return list((await self.session.scalars(stmt)).unique().all()), total

    def filtered_statement(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        category_id: uuid.UUID | None = None,
        category_code: str | None = None,
        grades: Sequence[str] | None = None,
        q: str | None = None,
    ) -> Select:
        stmt = (
            select(DailyReport)
            .join(Category, DailyReport.category_id == Category.id)
            .options(joinedload(DailyReport.category), selectinload(DailyReport.entries))
        )
        conditions = []
        if start:
            conditions.append(DailyReport.report_date >= start)
        if end:
            conditions.append(DailyReport.report_date <= end)
        if category_id:
            conditions.append(DailyReport.category_id == category_id)
        if category_code:
            conditions.append(Category.code == category_code)
        if q:
            like = f"%{q.strip()}%"
            conditions.append(
                DailyReport.note.ilike(like)
                | Category.title_template.ilike(like)
                | DailyReport.report_date.cast(String).ilike(f"%{q.strip()}%")
            )
        if conditions:
            stmt = stmt.where(and_(*conditions))
        if grades:
            sub = select(DailyGradeEntry.report_id).where(DailyGradeEntry.grade.in_(list(grades)))
            stmt = stmt.where(DailyGradeEntry.report_id.in_(sub))
        return stmt.order_by(DailyReport.report_date.desc(), Category.position.asc())

    # ----------------------------------------------------------- aggregates
    async def totals_between(
        self, start: date, end: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> dict[str, int]:
        stmt = select(*_sum_metrics()).where(
            DailyReport.report_date >= start, DailyReport.report_date <= end
        )
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        total, female, pp, kp = (await self.session.execute(stmt)).one()
        return {"total": int(total), "female": int(female), "pp": int(pp), "kp": int(kp)}

    async def totals_for_date(
        self, report_date: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> dict[str, int]:
        return await self.totals_between(report_date, report_date, category_ids=category_ids)

    async def cumulative_as_of(
        self, as_of: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> dict[str, int]:
        """Sum of every gain recorded up to and including ``as_of``."""
        stmt = select(*_sum_metrics()).where(DailyReport.report_date <= as_of)
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        total, female, pp, kp = (await self.session.execute(stmt)).one()
        return {"total": int(total), "female": int(female), "pp": int(pp), "kp": int(kp)}

    async def cumulative_by_category_as_of(self, as_of: date) -> dict[uuid.UUID, dict[str, int]]:
        stmt = (
            select(DailyReport.category_id, *_sum_metrics())
            .where(DailyReport.report_date <= as_of)
            .group_by(DailyReport.category_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {
            category_id: {"total": int(t), "female": int(f), "pp": int(p), "kp": int(k)}
            for category_id, t, f, p, k in rows
        }

    async def cumulative_grades_as_of(
        self, as_of: date, category_id: uuid.UUID | None = None
    ) -> dict[str, dict[str, int]]:
        stmt = (
            select(
                DailyGradeEntry.grade,
                func.coalesce(func.sum(DailyGradeEntry.today_total), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_female), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_pp), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_kp), 0),
            )
            .join(DailyReport, DailyGradeEntry.report_id == DailyReport.id)
            .where(DailyReport.report_date <= as_of)
        )
        if category_id:
            stmt = stmt.where(DailyReport.category_id == category_id)
        stmt = stmt.group_by(DailyGradeEntry.grade)
        return {
            grade: {"total": int(t), "female": int(f), "pp": int(p), "kp": int(k)}
            for grade, t, f, p, k in (await self.session.execute(stmt)).all()
        }

    async def grade_totals_between(
        self, start: date, end: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> dict[str, dict[str, int]]:
        stmt = (
            select(
                DailyGradeEntry.grade,
                func.coalesce(func.sum(DailyGradeEntry.today_total), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_female), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_pp), 0),
                func.coalesce(func.sum(DailyGradeEntry.today_kp), 0),
            )
            .join(DailyReport, DailyGradeEntry.report_id == DailyReport.id)
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
        )
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        stmt = stmt.group_by(DailyGradeEntry.grade)
        return {
            grade: {"total": int(t), "female": int(f), "pp": int(p), "kp": int(k)}
            for grade, t, f, p, k in (await self.session.execute(stmt)).all()
        }

    async def daily_series(
        self, start: date, end: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> list[dict[str, Any]]:
        stmt = (
            select(DailyReport.report_date, *_sum_metrics())
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
        )
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        stmt = stmt.group_by(DailyReport.report_date).order_by(DailyReport.report_date.asc())
        return [
            {
                "date": row[0],
                "total": int(row[1]),
                "female": int(row[2]),
                "pp": int(row[3]),
                "kp": int(row[4]),
            }
            for row in (await self.session.execute(stmt)).all()
        ]

    async def monthly_series(
        self, start: date, end: date, *, category_ids: Sequence[uuid.UUID] | None = None
    ) -> list[dict[str, Any]]:
        month = func.to_char(DailyReport.report_date, "YYYY-MM").label("period")
        stmt = (
            select(
                month,
                *_sum_metrics(),
                func.count(func.distinct(DailyReport.report_date)).label("active_days"),
            )
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
        )
        if category_ids:
            stmt = stmt.where(DailyReport.category_id.in_(list(category_ids)))
        stmt = stmt.group_by(month).order_by(month.asc())
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "period": row[0],
                "total": int(row[1]),
                "female": int(row[2]),
                "pp": int(row[3]),
                "kp": int(row[4]),
                "active_days": int(row[5]),
            }
            for row in rows
        ]

    async def by_category_totals(
        self, start: date, end: date
    ) -> dict[uuid.UUID, dict[str, int]]:
        stmt = (
            select(DailyReport.category_id, *_sum_metrics())
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
            .group_by(DailyReport.category_id)
        )
        return {
            category_id: {"total": int(t), "female": int(f), "pp": int(p), "kp": int(k)}
            for category_id, t, f, p, k in (await self.session.execute(stmt)).all()
        }

    async def weekdays(self, start: date, end: date) -> dict[str, int]:
        stmt = (
            select(func.to_char(DailyReport.report_date, "FMDay"), func.sum(DailyReport.today_total))
            .where(DailyReport.report_date >= start, DailyReport.report_date <= end)
            .group_by(func.to_char(DailyReport.report_date, "FMDay"))
        )
        return {name: int(value or 0) for name, value in (await self.session.execute(stmt)).all()}

    async def grade_d_total_on(self, report_date: date) -> int:
        stmt = select(func.coalesce(func.sum(DailyGradeEntry.today_total), 0)).where(
            DailyGradeEntry.grade == "D", DailyGradeEntry.report_id.in_(select(DailyReport.id).where(DailyReport.report_date == report_date))
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def latest_date(self) -> date | None:
        stmt = select(func.max(DailyReport.report_date))
        return (await self.session.execute(stmt)).scalar_one()

    async def first_date(self) -> date | None:
        stmt = select(func.min(DailyReport.report_date))
        return (await self.session.execute(stmt)).scalar_one()

    # ------------------------------------------------------------ snapshots
    async def replace_snapshot(
        self, report_date: date, category_id: uuid.UUID, payload: dict[str, Any]
    ) -> DailyTotalsSnapshot:
        snapshot = await self.get_snapshot(report_date, category_id)
        if snapshot is None:
            snapshot = DailyTotalsSnapshot(
                report_date=report_date, category_id=category_id, **payload
            )
            self.session.add(snapshot)
        else:
            for key, value in payload.items():
                setattr(snapshot, key, value)
        await self.session.flush()
        return snapshot

    async def get_snapshot(self, report_date: date, category_id: uuid.UUID) -> DailyTotalsSnapshot | None:
        stmt = select(DailyTotalsSnapshot).where(
            DailyTotalsSnapshot.report_date == report_date,
            DailyTotalsSnapshot.category_id == category_id,
        )
        return (await self.session.scalars(stmt)).first()

    async def snapshots_between(self, start: date, end: date) -> list[DailyTotalsSnapshot]:
        stmt = (
            select(DailyTotalsSnapshot)
            .options(joinedload(DailyTotalsSnapshot.category))
            .where(
                DailyTotalsSnapshot.report_date >= start, DailyTotalsSnapshot.report_date <= end
            )
            .order_by(DailyTotalsSnapshot.report_date.asc())
        )
        return list((await self.session.scalars(stmt)).unique().all())

    async def delete_snapshots_from(self, report_date: date) -> int:
        result = await self.session.execute(
            delete(DailyTotalsSnapshot).where(DailyTotalsSnapshot.report_date >= report_date)
        )
        return int(result.rowcount or 0)

    async def rebuild_all_snapshots(self) -> int:
        """Recompute every stored snapshot from the source rows."""
        dates = (
            await self.session.execute(
                select(func.distinct(DailyReport.report_date)).order_by(DailyReport.report_date)
            )
        ).scalars().all()
        await self.delete_snapshots_from(dates[0]) if dates else 0
        count = 0
        for report_date in dates:
            count += await self.recompute_from(report_date)
        return count


class DailyGradeEntryRepository(BaseRepository[DailyGradeEntry]):
    model = DailyGradeEntry

    async def list_for_report(self, report_id: uuid.UUID) -> list[DailyGradeEntry]:
        return list(
            (
                await self.session.scalars(
                    select(DailyGradeEntry)
                    .where(DailyGradeEntry.report_id == report_id)
                    .order_by(DailyGradeEntry.position.asc())
                )
            ).all()
        )

    async def delete_for_report(self, report_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(DailyGradeEntry).where(DailyGradeEntry.report_id == report_id)
        )
        return int(result.rowcount or 0)
