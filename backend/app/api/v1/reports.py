"""Daily report CRUD, history, search, summary and cumulative endpoints."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from typing_extensions import Annotated

from app.api.deps import (
    CurrentUser,
    Pagination,
    RequireManager,
    RequireStaff,
    get_cumulative_service,
    get_report_service,
)
from app.core.pagination import local_today, month_bounds
from app.models.enums import GradeLetter
from app.schemas.common import Counters, MessageResponse, Page
from app.schemas.report import (
    DailyReportBulkCreate,
    DailyReportCreate,
    DailyReportDetail,
    DailyReportRead,
    DailyReportUpdate,
    DeleteResult,
    SearchResponse,
    SnapshotRead,
)
from app.schemas.analytics import SummaryResponse
from app.services.cumulative_service import CumulativeService
from app.services.report_service import DailyReportService

router = APIRouter(prefix="/reports", tags=["Daily Reports"])


# ------------------------------------------------------------------- reads
@router.get(
    "",
    response_model=Page[DailyReportRead],
    summary="List daily reports (paginated, filterable)",
)
@router.get(
    "/history",
    response_model=Page[DailyReportRead],
    summary="List daily reports history (paginated, filterable)",
)
async def list_reports(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    pagination: Pagination,
    user: CurrentUser,
    start: Annotated[date | None, Query(description="Inclusive start date")] = None,
    end: Annotated[date | None, Query(description="Inclusive end date")] = None,
    category_id: UUID | None = None,
    category_code: str | None = None,
    grade: Annotated[list[GradeLetter] | None, Query()] = None,
    q: Annotated[str | None, Query(max_length=120, description="Free-text search")] = None,
) -> Page[DailyReportRead]:
    page = await service.history(
        page=pagination.page,
        size=pagination.size,
        start=start,
        end=end,
        category_id=category_id,
        category_code=category_code,
        grades=[g.value for g in grade] if grade else None,
        q=q,
    )
    return Page(
        items=await service.to_read_list(page.items),
        meta=page.meta,
    )


@router.get(
    "/dates",
    summary="Every date that has at least one report (newest first)",
)
async def list_dates(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
) -> list[str]:
    return [d.isoformat() for d in await service.list_dates(start, end)]


@router.get(
    "/today",
    response_model=list[DailyReportRead],
    summary="All categories for a single date (defaults to today)",
)
async def get_day(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    report_date: date | None = None,
    include_missing: Annotated[bool, Query(description="Include categories without a report")] = True,
) -> list[DailyReportRead]:
    target = report_date or local_today()
    reports = await service.get_by_date(target, include_missing=include_missing)
    return await service.to_read_list(reports)


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Search by date, category or free text",
)
async def search_reports(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    q: Annotated[str, Query(min_length=1, max_length=120, description="Date, category or keyword")],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> SearchResponse:
    results = await service.search(q, limit=limit)
    return SearchResponse(query=q, results=results, total=len(results))


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Cumulative summary for a date range",
)
async def summary(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
) -> SummaryResponse:
    today = local_today()
    end = end or today
    start = start or month_bounds(today)[0]
    return await service.summary_for(start, end, scope="range")


@router.get(
    "/summary/monthly",
    response_model=SummaryResponse,
    summary="Monthly summary",
)
async def monthly_summary(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int, Query(ge=1, le=12)] = None,
) -> SummaryResponse:
    today = local_today()
    target_year = year or today.year
    target_month = month or today.month
    return await service.monthly_summary(target_year, target_month)


@router.get(
    "/cumulative",
    summary="Cumulative totals per category as of a date",
)
async def cumulative(
    service: Annotated[CumulativeService, Depends(get_cumulative_service)],
    user: CurrentUser,
    as_of: date | None = None,
    category_code: str | None = None,
    end_date: date | None = None,
) -> dict:
    target = end_date or as_of or local_today()
    if category_code:
        categories = await service._active_categories()
        matching = [c for c in categories if c.code == category_code]
        if not matching:
            return {
                "category_code": category_code,
                "as_of": target,
                "cumulative": {"total": 0, "female": 0, "pp": 0, "kp": 0},
                "history": [],
            }
        cat = matching[0]
        from sqlalchemy import select
        from app.models.report import DailyReport
        stmt = (
            select(DailyReport)
            .where(DailyReport.category_id == cat.id, DailyReport.report_date <= target)
            .order_by(DailyReport.report_date.asc())
        )
        reports = list((await service.session.scalars(stmt)).all())
        history = []
        running_tot = 0
        running_fem = 0
        running_pp = 0
        running_kp = 0
        for r in reports:
            running_tot += r.today_total
            running_fem += r.today_female
            running_pp += r.today_pp
            running_kp += r.today_kp
            history.append({
                "report_date": r.report_date.isoformat(),
                "today": {"total": r.today_total, "female": r.today_female, "pp": r.today_pp, "kp": r.today_kp},
                "cumulative": {"total": running_tot, "female": running_fem, "pp": running_pp, "kp": running_kp},
            })
        return {
            "category_code": category_code,
            "as_of": target,
            "cumulative": {"total": running_tot, "female": running_fem, "pp": running_pp, "kp": running_kp},
            "history": history,
        }

    items = await service.cumulative_by_category(target)
    return {
        "as_of": target,
        "grand_total": await service.grand_total(target),
        "categories": [
            {
                "category_id": item.category_id,
                "category_code": item.category_code,
                **item.as_dict(),
                "male": item.male,
            }
            for item in items
        ],
    }


@router.get(
    "/cumulative/series",
    summary="Day-by-day cumulative series (carries days without entries forward)",
)
async def cumulative_series(
    service: Annotated[CumulativeService, Depends(get_cumulative_service)],
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
    category_id: UUID | None = None,
) -> dict:
    today = local_today()
    end = end or today
    start = start or month_bounds(today)[0]
    if end < start:
        start, end = end, start
    category_ids = [category_id] if category_id else None
    series = await service.cumulative_series(start, end, category_ids=category_ids)
    # Grade split of the students gained in the same range (drives the donut).
    grades = await service.repo.grade_totals_between(start, end, category_ids=category_ids)
    return {"start": start, "end": end, "points": series, "grades": grades}


@router.get(
    "/cumulative/snapshots",
    response_model=list[SnapshotRead],
    summary="Stored cumulative snapshots for a range (diagnostics / audit)",
)
async def snapshots(
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
) -> list[SnapshotRead]:
    today = local_today()
    end = end or today
    start = start or month_bounds(today)[0]
    rows = await service.repo.snapshots_between(start, end)
    year = await service.settings.get_current_year()
    return [
        SnapshotRead(
            report_date=row.report_date,
            category_id=row.category_id,
            category_code=row.category.code,
            cumulative=Counters(
                total=row.cumulative_total,
                female=row.cumulative_female,
                pp=row.cumulative_pp,
                kp=row.cumulative_kp,
            ),
            grade_cumulative={
                grade: Counters(**values)
                for grade, values in (row.grade_cumulative or {}).items()
            },
            computed_at=row.computed_at,
        )
        for row in rows
    ]


@router.get(
    "/{report_id}",
    response_model=DailyReportDetail,
    summary="Fetch a single report with its cumulative split",
)
@router.get(
    "/daily/{report_id}",
    response_model=DailyReportDetail,
    summary="Fetch a single report with its cumulative split",
)
async def get_report(
    report_id: UUID,
    service: Annotated[DailyReportService, Depends(get_report_service)],
    user: CurrentUser,
) -> DailyReportDetail:
    report = await service.get_or_raise(report_id)
    read = await service.to_read(report)
    cumulative = await service.cumulative.cumulative_for_category(
        report.report_date, str(report.category_id)
    )
    return DailyReportDetail(
        **read.model_dump(),
        grade_cumulative={grade: cumulative.grade_counters(grade) for grade in cumulative.grade_total},
        male=max(read.cumulative.total - read.cumulative.female, 0),
        is_consistent=report.is_grade_consistent,
    )


# ------------------------------------------------------------------ writes
@router.post(
    "",
    response_model=DailyReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record today's gain for one category",
)
@router.post(
    "/daily",
    response_model=DailyReportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record today's gain for one category",
)
async def create_report(
    payload: DailyReportCreate,
    service: Annotated[DailyReportService, Depends(get_report_service)],
    actor: RequireStaff,
) -> DailyReportRead:
    report = await service.create(payload)
    await service.session.commit()
    return await service.to_read(report)


@router.post(
    "/bulk",
    response_model=list[DailyReportRead],
    status_code=status.HTTP_201_CREATED,
    summary="Record several categories for one date in a single transaction",
)
async def create_reports(
    payload: DailyReportBulkCreate,
    service: Annotated[DailyReportService, Depends(get_report_service)],
    actor: RequireStaff,
) -> list[DailyReportRead]:
    reports = await service.bulk_create(payload.reports)
    await service.session.commit()
    return await service.to_read_list(reports)


@router.patch(
    "/{report_id}",
    response_model=DailyReportRead,
    summary="Edit a report (cumulative totals recalculate automatically)",
)
@router.patch(
    "/daily/{report_id}",
    response_model=DailyReportRead,
    summary="Edit a report (cumulative totals recalculate automatically)",
)
async def update_report(
    report_id: UUID,
    payload: DailyReportUpdate,
    service: Annotated[DailyReportService, Depends(get_report_service)],
    actor: RequireStaff,
) -> DailyReportRead:
    report = await service.update(report_id, payload)
    await service.session.commit()
    return await service.to_read(report)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a report and re-base every later cumulative value",
)
@router.delete(
    "/daily/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a report and re-base every later cumulative value",
)
async def delete_report(
    report_id: UUID,
    service: Annotated[DailyReportService, Depends(get_report_service)],
    actor: RequireManager,
) -> Response:
    await service.delete(report_id)
    await service.session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/recompute",
    response_model=MessageResponse,
    summary="Rebuild every cumulative snapshot from the ledger",
)
async def recompute(
    service: Annotated[CumulativeService, Depends(get_cumulative_service)],
    actor: RequireManager,
) -> MessageResponse:
    count = await service.recompute_all()
    await service.session.commit()
    return MessageResponse(message=f"Recomputed {count} cumulative snapshot(s).")
