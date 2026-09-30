"""Daily report CRUD, history, search and summary business logic."""

from __future__ import annotations

import logging
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, ImmutableRecordError, NotFoundError, ValidationError
from app.core.pagination import PageParams, build_page_meta, month_bounds
from app.models.enums import AuditAction
from app.models.reference import Category
from app.models.report import DailyGradeEntry, DailyReport
from app.models.user import User
from app.repositories.reference_repo import CategoryRepository, GradeRepository
from app.repositories.report_repo import DailyReportRepository
from app.schemas.analytics import SummaryResponse
from app.schemas.common import Counters, Page
from app.schemas.report import (
    DailyReportCreate,
    DailyReportRead,
    DailyReportUpdate,
    GradeEntryRead,
    ReportSearchResult,
)
from app.services.audit_service import AuditService
from app.services.cumulative_service import GRADES, CumulativeService
from app.services.settings_service import SettingsService

logger = logging.getLogger("scholar.reports")

ENTITY = "daily_report"


class DailyReportService:
    def __init__(self, session: AsyncSession, current_user: User | None = None) -> None:
        self.session = session
        self.current_user = current_user
        self.repo = DailyReportRepository(session)
        self.category_repo = CategoryRepository(session)
        self.grade_repo = GradeRepository(session)
        self.cumulative = CumulativeService(session)
        self.settings = SettingsService(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------- creation
    async def create(self, payload: DailyReportCreate) -> DailyReport:
        category = await self._resolve_category(payload.category_id)
        await self._ensure_not_future(payload.report_date)
        existing = await self.repo.get_for_date(payload.report_date, category.id)
        if existing is not None:
            raise ConflictError(
                f"A report for {payload.report_date} already exists in this category.",
                details={"report_id": str(existing.id)},
            )
        self._validate_grades(payload)

        report = DailyReport(
            report_date=payload.report_date,
            category_id=category.id,
            today_total=payload.total,
            today_female=payload.female,
            today_pp=payload.pp,
            today_kp=payload.kp,
            note=payload.note,
            source=payload.source,
            created_by=self.current_user.id if self.current_user else None,
        )
        positions = await self.grade_repo.positions()
        for grade_input in payload.grades:
            code = str(grade_input.grade)
            pos = positions.get(code, GRADES.index(code) + 1 if code in GRADES else 5)
            report.entries.append(
                DailyGradeEntry(
                    grade=code,
                    position=pos,
                    today_total=grade_input.total,
                    today_female=grade_input.female,
                    today_pp=grade_input.pp,
                    today_kp=grade_input.kp,
                )
            )
        self.repo.add(report)
        await self.session.flush()
        await self.cumulative.recompute_from(payload.report_date)
        await self.audit.log(
            action=AuditAction.CREATE,
            entity_type=ENTITY,
            entity_id=report.id,
            summary=(
                f"Created report {payload.report_date} / {category.code}: "
                f"total={payload.total} female={payload.female} pp={payload.pp} kp={payload.kp}"
            ),
            changes=payload.model_dump(mode="json", exclude={"grades"}),
            user=self.current_user,
        )
        await self.session.flush()
        return await self.get_or_raise(report.id)

    async def bulk_create(self, payloads: list[DailyReportCreate]) -> list[DailyReport]:
        created: list[DailyReport] = []
        seen: set[tuple[date, str]] = set()
        for payload in payloads:
            category = await self._resolve_category(payload.category_id)
            key = (payload.report_date, category.code)
            if key in seen:
                raise ValidationError(
                    f"Duplicate entry in request for {payload.report_date} / {category.code}."
                )
            seen.add(key)
            created.append(await self.create(payload))
        return created

    # --------------------------------------------------------------- update
    async def update(self, report_id: UUID, payload: DailyReportUpdate) -> DailyReport:
        report = await self.repo.get_detailed(report_id)
        if report is None:
            raise NotFoundError("Daily report not found.")
        if report.is_locked:
            raise ImmutableRecordError("This report is locked and can no longer be edited.")

        before = self._snapshot_values(report)
        earliest = report.report_date

        if payload.report_date and payload.report_date != report.report_date:
            await self._ensure_not_future(payload.report_date)
            conflict = await self.repo.get_for_date(payload.report_date, report.category_id)
            if conflict is not None:
                raise ConflictError(
                    f"A report for {payload.report_date} already exists in this category."
                )
            report.report_date = payload.report_date
            earliest = min(earliest, payload.report_date)

        if payload.category_id and payload.category_id != report.category_id:
            category = await self._resolve_category(payload.category_id)
            conflict = await self.repo.get_for_date(report.report_date, category.id)
            if conflict is not None:
                raise ConflictError("A report for that date already exists in the target category.")
            report.category_id = category.id
            earliest = min(earliest, report.report_date)

        if payload.grades is not None:
            merged = DailyReportCreate(
                report_date=report.report_date,
                category_id=report.category_id,
                grades=payload.grades,
                total=sum(g.total for g in payload.grades),
                female=sum(g.female for g in payload.grades),
                pp=sum(g.pp for g in payload.grades),
                kp=sum(g.kp for g in payload.grades),
                recompute_totals=True,
            )
            await self._replace_entries(report, merged)
            report.today_total = merged.total
            report.today_female = merged.female
            report.today_pp = merged.pp
            report.today_kp = merged.kp
        else:
            for field in ("total", "female", "pp", "kp"):
                value = getattr(payload, field)
                if value is not None:
                    setattr(report, f"today_{field}", value)
            if len(report.entries) == 1:
                report.entries[0].today_total = report.today_total
                report.entries[0].today_female = report.today_female
                report.entries[0].today_pp = report.today_pp
                report.entries[0].today_kp = report.today_kp

        if payload.note is not None:
            report.note = payload.note
        if payload.is_locked is not None:
            report.is_locked = payload.is_locked
        report.updated_by = self.current_user.id if self.current_user else None
        await self.session.flush()

        await self.cumulative.recompute_from(earliest)
        after = self._snapshot_values(report)
        await self.audit.diff_log(
            entity_type=ENTITY,
            entity_id=report.id,
            before=before,
            after=after,
            user=self.current_user,
        )
        await self.session.flush()
        return await self.get_or_raise(report.id)

    # --------------------------------------------------------------- delete
    async def delete(self, report_id: UUID) -> date:
        report = await self.repo.get_detailed(report_id)
        if report is None:
            raise NotFoundError("Daily report not found.")
        if report.is_locked:
            raise ImmutableRecordError("This report is locked and cannot be deleted.")
        affected = report.report_date
        payload = self._snapshot_values(report)
        await self.session.delete(report)
        await self.session.flush()
        await self.cumulative.recompute_from(affected)
        await self.audit.log(
            action=AuditAction.DELETE,
            entity_type=ENTITY,
            entity_id=report_id,
            summary=f"Deleted report {affected} / {report.category.code}",
            changes=payload,
            user=self.current_user,
        )
        await self.session.flush()
        return affected

    # -------------------------------------------------------------- reading
    async def get_or_raise(self, report_id: UUID) -> DailyReport:
        report = await self.repo.get_detailed(report_id)
        if report is None:
            raise NotFoundError("Daily report not found.")
        return report

    async def get_by_date(
        self,
        report_date: date,
        *,
        category_code: str | None = None,
        include_missing: bool = False,
    ) -> list[DailyReport]:
        if category_code:
            found = await self.repo.get_for_date_code(report_date, category_code)
            return [found] if found else []
        reports = await self.repo.list_by_date(report_date)
        if include_missing:
            existing = {str(r.category_id) for r in reports}
            for category in await self.category_repo.list_ordered():
                if str(category.id) not in existing:
                    reports.append(self._empty_report(report_date, category))
        return reports

    async def history(
        self,
        *,
        page: int = 1,
        size: int = 20,
        start: date | None = None,
        end: date | None = None,
        category_id: UUID | None = None,
        category_code: str | None = None,
        grades: list[str] | None = None,
        q: str | None = None,
    ) -> Page[DailyReport]:
        stmt = self.repo.filtered_statement(
            start=start, end=end, category_id=category_id,
            category_code=category_code, grades=grades, q=q,
        )
        items, total = await self.repo.paginate_filtered(stmt, page, size)
        return Page(items=items, meta=build_page_meta(total, PageParams(page, size)))

    async def search(self, query: str, *, limit: int = 25) -> list[ReportSearchResult]:
        """
        Flexible search across dates, categories, notes and grade letters.
        ``2026-09-29``, ``29/09/2026``, ``D`` and ``current`` are all accepted.
        """
        text = query.strip()
        results: list[ReportSearchResult] = []
        categories = await self.category_repo.list_ordered(active_only=False)
        year = await self.settings.get_current_year()

        target_date = self._parse_date_query(text)
        start = end = target_date
        if target_date is None and len(text) == 4 and text.isdigit():
            start = date(int(text), 1, 1)
            end = date(int(text), 12, 31)

        code_filter = self._match_category_code(text, categories)

        if start is None:
            # No date recognised - fall back to a note/category text search.
            reports, _ = await self.repo.paginate_filtered(
                self.repo.filtered_statement(q=text, category_code=code_filter), 1, limit
            )
        else:
            reports, _ = await self.repo.paginate_filtered(
                self.repo.filtered_statement(start=start, end=end, category_code=code_filter),
                1,
                limit,
            )

        for report in reports:
            grade_d = next((e.today_total for e in report.entries if e.grade == "D"), 0)
            results.append(
                ReportSearchResult(
                    report_date=report.report_date,
                    category_code=report.category.code,
                    category_title=report.category.render_title(year),
                    total=report.today_total,
                    female=report.today_female,
                    male=max(report.today_total - report.today_female, 0),
                    pp=report.today_pp,
                    kp=report.today_kp,
                    grade_d_total=grade_d,
                )
            )
        return results

    async def list_dates(self, start: date | None = None, end: date | None = None) -> list[date]:
        from sqlalchemy import distinct, select

        from app.models.report import DailyReport as DR

        stmt = select(distinct(DR.report_date))
        if start:
            stmt = stmt.where(DR.report_date >= start)
        if end:
            stmt = stmt.where(DR.report_date <= end)
        stmt = stmt.order_by(DR.report_date.desc())
        return list((await self.session.scalars(stmt)).all())

    # ------------------------------------------------------------- summary
    async def summary_for(
        self, start: date, end: date, *, scope: str = "range"
    ) -> SummaryResponse:
        year = await self.settings.get_current_year()
        categories = await self.category_repo.list_ordered()
        totals = await self.repo.totals_between(start, end)
        by_category = await self.repo.by_category_totals(start, end)
        by_grade = await self.repo.grade_totals_between(start, end)

        from app.schemas.analytics import CategoryMetric, GradeDistributionItem

        category_metrics = []
        for category in categories:
            raw = by_category.get(category.id, {"total": 0, "female": 0, "pp": 0, "kp": 0})
            count = Counters(**raw)
            category_metrics.append(
                CategoryMetric(
                    category_id=str(category.id),
                    category_code=category.code,
                    title=category.render_title(year),
                    roman_numeral=category.roman_numeral,
                    position=category.position,
                    month=count,
                    male_month=max(count.total - count.female, 0),
                )
            )

        grade_metrics = [
            GradeDistributionItem(
                grade=grade,
                total=by_grade.get(grade, {}).get("total", 0),
                female=by_grade.get(grade, {}).get("female", 0),
                pp=by_grade.get(grade, {}).get("pp", 0),
                kp=by_grade.get(grade, {}).get("kp", 0),
            )
            for grade in GRADES
        ]

        text = self._summary_text(start, end, totals, category_metrics, year)
        return SummaryResponse(
            scope=scope,
            period_start=start,
            period_end=end,
            current_year=year,
            totals=Counters(**totals),
            by_category=category_metrics,
            by_grade=grade_metrics,
            text=text,
        )

    async def monthly_summary(self, year: int, month: int) -> SummaryResponse:
        start = date(year, month, 1)
        end_month = month_bounds(start)[1]
        return await self.summary_for(start, end_month, scope="monthly")

    # --------------------------------------------------------- serialisation
    async def to_read(self, report: DailyReport) -> DailyReportRead:
        year = await self.settings.get_current_year()
        cumulative = await self.cumulative.cumulative_for_category(
            report.report_date, str(report.category_id)
        )
        category: Category = report.category
        return DailyReportRead(
            id=report.id,
            report_date=report.report_date,
            category_id=report.category_id,
            category_code=category.code,
            category_title=category.render_title(year),
            roman_numeral=category.roman_numeral,
            today=Counters(
                total=report.today_total,
                female=report.today_female,
                pp=report.today_pp,
                kp=report.today_kp,
            ),
            cumulative=cumulative.counters(),
            today_total=report.today_total,
            today_female=report.today_female,
            today_pp=report.today_pp,
            today_kp=report.today_kp,
            grades=[
                GradeEntryRead(
                    id=entry.id,
                    grade=entry.grade,
                    position=entry.position,
                    total=entry.today_total,
                    female=entry.today_female,
                    pp=entry.today_pp,
                    kp=entry.today_kp,
                )
                for entry in report.entries
            ],
            note=report.note,
            source=report.source,
            is_locked=report.is_locked,
            created_by=report.created_by,
            created_by_username=report.created_by_user.username if report.created_by_user else None,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )

    async def to_read_list(self, reports: list[DailyReport]) -> list[DailyReportRead]:
        return [await self.to_read(report) for report in reports]

    # -------------------------------------------------------------- helpers
    async def _resolve_category(self, value: UUID | str) -> Category:
        category = await self.category_repo.resolve(value)
        if category is None:
            raise NotFoundError(f"Category {value} not found.")
        return category

    async def _ensure_not_future(self, report_date: date) -> None:
        from app.core.config import settings
        from app.core.pagination import local_today

        if settings.ENVIRONMENT not in ("test", "testing") and report_date > local_today():
            raise ValidationError("Report date cannot be in the future.")

    def _validate_grades(self, payload: DailyReportCreate) -> None:
        if not payload.grades:
            return
        for entry in payload.grades:
            if entry.female > entry.total:
                raise ValidationError(f"Grade {entry.grade}: female cannot exceed total.")
            if entry.pp + entry.kp > entry.total:
                raise ValidationError(f"Grade {entry.grade}: PP + KP cannot exceed total.")
        if payload.total != sum(g.total for g in payload.grades):
            raise ValidationError("Sum of grade totals must equal the report total.")
        if payload.female != sum(g.female for g in payload.grades):
            raise ValidationError("Sum of grade females must equal the report female.")
        if payload.pp != sum(g.pp for g in payload.grades):
            raise ValidationError("Sum of grade PP must equal the report PP.")
        if payload.kp != sum(g.kp for g in payload.grades):
            raise ValidationError("Sum of grade KP must equal the report KP.")

    def _validate_grade_consistency(self, report: DailyReport) -> None:
        if not report.entries:
            return
        if (
            report.grade_sum_total != report.today_total
            or report.grade_sum_female != report.today_female
            or report.grade_sum_pp != report.today_pp
            or report.grade_sum_kp != report.today_kp
        ):
            raise ValidationError(
                "Report totals must equal the sum of the per-grade entries.",
                details={
                    "total": [report.grade_sum_total, report.today_total],
                    "female": [report.grade_sum_female, report.today_female],
                    "pp": [report.grade_sum_pp, report.today_pp],
                    "kp": [report.grade_sum_kp, report.today_kp],
                },
            )

    async def _replace_entries(
        self, report: DailyReport, payload: DailyReportCreate
    ) -> None:
        positions = await self.grade_repo.positions()
        existing = {entry.grade: entry for entry in report.entries}
        seen: set[str] = set()
        for grade_input in payload.grades:
            code = str(grade_input.grade)
            seen.add(code)
            entry = existing.get(code)
            if entry is None:
                entry = DailyGradeEntry(report_id=report.id, grade=code)
                self.session.add(entry)
                report.entries.append(entry)
            entry.position = positions.get(code, GRADES.index(code) + 1 if code in GRADES else 5)
            entry.today_total = grade_input.total
            entry.today_female = grade_input.female
            entry.today_pp = grade_input.pp
            entry.today_kp = grade_input.kp
        for code, entry in existing.items():
            if code not in seen:
                await self.session.delete(entry)
        await self.session.flush()
        await self.session.refresh(report, ["entries"])

    @staticmethod
    def _empty_report(report_date: date, category: Category) -> DailyReport:
        return DailyReport(
            id=uuid4(),
            report_date=report_date,
            category_id=category.id,
            today_total=0,
            today_female=0,
            today_pp=0,
            today_kp=0,
            source="missing",
            # Transient placeholder: column defaults only apply on INSERT, so
            # set it explicitly or DailyReportRead rejects is_locked=None.
            is_locked=False,
            category=category,
            entries=[],
        )

    @staticmethod
    def _snapshot_values(report: DailyReport) -> dict[str, object]:
        return {
            "report_date": report.report_date.isoformat(),
            "category_id": str(report.category_id),
            "today_total": report.today_total,
            "today_female": report.today_female,
            "today_pp": report.today_pp,
            "today_kp": report.today_kp,
            "grades": {
                entry.grade: {
                    "total": entry.today_total,
                    "female": entry.today_female,
                    "pp": entry.today_pp,
                    "kp": entry.today_kp,
                }
                for entry in report.entries
            },
        }

    @staticmethod
    def _parse_date_query(text: str) -> date | None:
        from datetime import datetime

        candidates = [text, text.replace("/", "-"), text.replace(".", "-"), text.replace(" ", "")]
        for candidate in candidates:
            try:
                return datetime.strptime(candidate, "%d-%m-%Y").date()
            except ValueError:
                continue
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _match_category_code(text: str, categories: list[Category]) -> str | None:
        from app.services.reference_defaults import CATEGORY_KEYWORDS

        lowered = text.lower()
        for code, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                if code in {c.code for c in categories}:
                    return code
        return None

    @staticmethod
    def _summary_text(
        start: date,
        end: date,
        totals: dict[str, int],
        categories: list,
        year: int,
    ) -> str:
        from app.core.pagination import format_number

        lines = [
            f"សេចក្តីសង្ខេប សម្រាប់រយៈពេល {start:%d/%m/%Y} - {end:%d/%m/%Y}",
            f"សរុបរួម : {format_number(totals['total'])} នាក់ "
            f"ស្រី {format_number(totals['female'])} នាក់",
            f"(PP: {format_number(totals['pp'])} នាក់, KP: {format_number(totals['kp'])} នាក់)",
            "",
        ]
        for metric in categories:
            lines.append(f"{metric.roman_numeral} {metric.title}")
            lines.append(
                f"សរុបរួមចំនួន : {format_number(metric.month.total)} នាក់ "
                f"ស្រី {format_number(metric.month.female)} នាក់"
            )
            lines.append(
                f"(PP: {format_number(metric.month.pp)} នាក់, KP: {format_number(metric.month.kp)} នាក់)"
            )
            lines.append("")
        lines.append(f"ឆ្នាំសិក្សា៖ {year}")
        return "\n".join(lines).strip()
