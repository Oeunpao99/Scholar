"""Student list endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, RequireManager, RequireStaff, get_student_service
from app.schemas.common import MessageResponse, Page
from app.schemas.student import Gender, GradeCode, Stream, StudentCreate, StudentRead, StudentUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("", response_model=Page[StudentRead], summary="List students")
async def list_students(
    service: Annotated[StudentService, Depends(get_student_service)],
    user: CurrentUser,
    pagination: Pagination,
    academic_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    gender: Gender | None = None,
    grade: GradeCode | None = None,
    stream: Stream | None = None,
) -> Page[StudentRead]:
    page = await service.list(
        page=pagination.page, size=pagination.size, academic_year=academic_year,
        q=q, gender=gender, grade=grade, stream=stream,
    )
    return Page(items=[StudentRead.model_validate(s) for s in page.items], meta=page.meta)


@router.get("/{student_id}", response_model=StudentRead, summary="Fetch a student")
async def get_student(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    user: CurrentUser,
) -> StudentRead:
    return StudentRead.model_validate(await service.get(student_id))


@router.post(
    "",
    response_model=StudentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a student",
)
async def create_student(
    payload: StudentCreate,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentRead:
    return StudentRead.model_validate(await service.create(payload))


@router.patch("/{student_id}", response_model=StudentRead, summary="Update a student")
async def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentRead:
    return StudentRead.model_validate(await service.update(student_id, payload))


@router.delete("/{student_id}", response_model=MessageResponse, summary="Delete a student")
async def delete_student(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireManager,
) -> MessageResponse:
    await service.delete(student_id)
    return MessageResponse(message="Student deleted.")
