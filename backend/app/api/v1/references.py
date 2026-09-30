"""Reference data endpoints (categories and grades)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_settings_service
from app.schemas.reference import CategoryRead, GradeRead
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/references", tags=["Reference Data"])


@router.get("/categories", summary="List categories")
async def list_categories(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> dict:
    year = await service.get_current_year()
    categories = await service.list_categories()
    items = [CategoryRead.from_entity(c, year).model_dump() for c in categories]
    return {"items": items, "total": len(items)}


@router.get("/grades", summary="List grades")
async def list_grades(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> dict:
    grades = await service.list_grades()
    items = [GradeRead.model_validate(g).model_dump() for g in grades]
    return {"items": items, "total": len(items)}
