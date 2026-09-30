"""Dashboard and statistics endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, get_dashboard_service
from app.schemas.analytics import (
    CategoryMetric,
    DashboardResponse,
    StatisticsResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    summary="Everything the dashboard needs in a single round trip",
)
async def dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    user: CurrentUser,
    date_: Annotated[date | None, Query(alias="date", description="Reference date")] = None,
    trend_days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> DashboardResponse:
    return await service.dashboard(reference_date=date_, trend_days=trend_days)


@router.get(
    "/categories",
    response_model=list[CategoryMetric],
    summary="Category overview (today / month / cumulative)",
)
async def categories(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    user: CurrentUser,
    date_: date | None = None,
) -> list[CategoryMetric]:
    return await service.category_overview(date_)


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    summary="Aggregated statistics for a period",
)
async def statistics(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    user: CurrentUser,
    start: date | None = None,
    end: date | None = None,
    category_id: UUID | None = None,
) -> StatisticsResponse:
    return await service.statistics(start=start, end=end, category_id=category_id)
