"""Reference data: settings, categories, grades and the current year."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    RequireAdmin,
    get_cumulative_service,
    get_settings_service,
)
from app.core.errors import NotFoundError
from app.models.reference import Category as CategoryEntity
from app.models.reference import Grade as GradeEntity
from app.repositories.reference_repo import CategoryRepository, GradeRepository
from app.schemas.common import MessageResponse
from app.schemas.reference import (
    CategoryCreate,
    CategoryRead,
    CategoryTitleUpdate,
    CategoryUpdate,
    GradeCreate,
    GradeRead,
    GradeUpdate,
    SettingRead,
    SettingUpdate,
    YearUpdate,
)
from app.repositories.reference_repo import CategoryRepository, GradeRepository
from app.services.cumulative_service import CumulativeService
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["Settings & Reference Data"])


# ----------------------------------------------------------------- settings
@router.get("", response_model=list[SettingRead], summary="All system settings")
async def list_settings(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> list[SettingRead]:
    return await service.list_settings()


@router.get("/current-year", summary="The configured academic year")
async def get_current_year(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> dict[str, int]:
    return {"current_year": await service.get_current_year()}


@router.put(
    "/current-year",
    response_model=MessageResponse,
    summary="Change the academic year (updates every category title)",
)
async def set_current_year(
    payload: YearUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> MessageResponse:
    await service.set_current_year(payload.current_year, actor.id)
    await service.repo.session.commit()
    return MessageResponse(
        message=f"Current year set to {payload.current_year}. Category titles were updated."
    )


@router.put(
    "/{key}",
    response_model=SettingRead,
    summary="Update a single setting",
)
async def update_setting(
    key: str,
    payload: SettingUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> SettingRead:
    try:
        result = await service.update_setting(key, payload.value, actor.id)
    except KeyError as exc:
        raise NotFoundError(f"Unknown setting: {key}") from exc
    await service.repo.session.commit()
    return result


# --------------------------------------------------------------- categories
@router.get("/categories", response_model=list[CategoryRead], summary="The three categories")
async def list_categories(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> list[CategoryRead]:
    year = await service.get_current_year()
    categories = await service.list_categories()
    return [CategoryRead.from_entity(c, year) for c in categories]


@router.post(
    "/categories",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
async def create_category(
    payload: CategoryCreate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> CategoryRead:
    year = await service.get_current_year()
    category = CategoryEntity(
        code=payload.code,
        position=payload.position,
        roman_numeral=payload.roman_numeral,
        title_template=payload.title_template,
        is_active=payload.is_active,
        description=payload.description,
    )
    service.categories.add(category)
    await service.repo.session.commit()
    return CategoryRead.from_entity(category, year)


@router.patch("/categories/{category_id}", response_model=CategoryRead, summary="Update a category")
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> CategoryRead:
    year = await service.get_current_year()
    category = await service.categories.get(category_id)
    if category is None:
        raise NotFoundError("Category not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    await service.repo.session.commit()
    return CategoryRead.from_entity(category, year)


@router.put(
    "/categories/{category_id}/title",
    response_model=CategoryRead,
    summary="Change a category title template",
)
async def update_category_title(
    category_id: UUID,
    payload: CategoryTitleUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> CategoryRead:
    year = await service.get_current_year()
    category = await service.categories.get(category_id)
    if category is None:
        raise NotFoundError("Category not found.")
    category.title_template = payload.title_template
    await service.repo.session.commit()
    return CategoryRead.from_entity(category, year)


# ------------------------------------------------------------------- grades
@router.get("/grades", response_model=list[GradeRead], summary="Available grades")
async def list_grades(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    user: CurrentUser,
) -> list[GradeRead]:
    return [GradeRead.model_validate(g) for g in await service.list_grades()]


@router.post(
    "/grades",
    response_model=GradeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a grade",
)
async def create_grade(
    payload: GradeCreate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> GradeRead:
    grade = GradeEntity(
        code=payload.code,
        position=payload.position,
        label=payload.label,
        is_active=payload.is_active,
        description=payload.description,
    )
    service.grades.add(grade)
    await service.repo.session.commit()
    return GradeRead.model_validate(grade)


@router.patch("/grades/{grade_id}", response_model=GradeRead, summary="Update a grade")
async def update_grade(
    grade_id: UUID,
    payload: GradeUpdate,
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> GradeRead:
    grade = await service.grades.get(grade_id)
    if grade is None:
        raise NotFoundError("Grade not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(grade, key, value)
    await service.repo.session.commit()
    return GradeRead.model_validate(grade)


# -------------------------------------------------------------- maintenance
@router.post(
    "/reseed",
    response_model=MessageResponse,
    summary="Recreate any missing reference data (categories, grades, settings)",
)
async def reseed(
    service: Annotated[SettingsService, Depends(get_settings_service)],
    actor: RequireAdmin,
) -> MessageResponse:
    await service.ensure_reference_data()
    await service.repo.session.commit()
    return MessageResponse(message="Reference data verified.")


@router.post(
    "/rebuild-cumulative",
    response_model=MessageResponse,
    summary="Rebuild every cumulative snapshot",
)
async def rebuild_cumulative(
    service: Annotated[CumulativeService, Depends(get_cumulative_service)],
    actor: RequireAdmin,
) -> MessageResponse:
    count = await service.recompute_all()
    await service.session.commit()
    return MessageResponse(message=f"Rebuilt {count} snapshot(s).")
