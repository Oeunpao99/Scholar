"""Student list endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status

from app.api.deps import CurrentUser, Pagination, RequireManager, RequireStaff, get_student_service
from app.core.config import settings
from app.core.errors import ValidationError
from app.schemas.common import MessageResponse, Page
from app.schemas.student import (
    Gender,
    GradeCode,
    Stream,
    StudentCreate,
    StudentExtraction,
    StudentImportResult,
    StudentRead,
    StudentUpdate,
)
from app.services.student_service import StudentService

router = APIRouter(prefix="/students", tags=["Students"])


async def _read_upload(file: UploadFile) -> bytes:
    limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise ValidationError(f"The file is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")
    return data


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
    return Page(items=await service.to_read(page.items), meta=page.meta)


@router.get("/export", summary="Export students list as Word (.docx), Excel (.xlsx), or PDF (.pdf)")
async def export_students(
    service: Annotated[StudentService, Depends(get_student_service)],
    user: CurrentUser,
    format: Annotated[str, Query(pattern="^(word|docx|excel|xlsx|pdf)$")] = "word",
    academic_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    gender: Gender | None = None,
    grade: GradeCode | None = None,
    stream: Stream | None = None,
) -> Response:
    payload, filename, media_type = await service.export(
        export_format=format,
        academic_year=academic_year,
        q=q,
        gender=gender,
        grade=grade,
        stream=stream,
    )
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post(
    "/extract",
    response_model=StudentExtraction,
    summary="Read a student's details and photo from an uploaded application form; nothing is saved",
)
async def extract_student(
    file: Annotated[UploadFile, File(description="Photo or scan of one application form (JPG, PNG, WebP or PDF)")],
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentExtraction:
    return await service.extract_from_file(await _read_upload(file), filename=file.filename)


@router.post(
    "/import",
    response_model=StudentImportResult,
    summary="Add students from a Word (.docx) or Excel (.xlsx) list",
)
async def import_students(
    file: Annotated[UploadFile, File(description="A .docx table or .xlsx sheet with a header row")],
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
    academic_year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
) -> StudentImportResult:
    return await service.import_from_file(await _read_upload(file), academic_year=academic_year)


@router.get("/{student_id}", response_model=StudentRead, summary="Fetch a student")
async def get_student(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    user: CurrentUser,
) -> StudentRead:
    return await service.read(await service.get(student_id))


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
    return await service.read(await service.create(payload))


@router.patch("/{student_id}", response_model=StudentRead, summary="Update a student")
async def update_student(
    student_id: UUID,
    payload: StudentUpdate,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentRead:
    return await service.read(await service.update(student_id, payload))


@router.delete("/{student_id}", response_model=MessageResponse, summary="Delete a student")
async def delete_student(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireManager,
) -> MessageResponse:
    await service.delete(student_id)
    return MessageResponse(message="Student deleted.")


# ------------------------------------------------------------------- photo
@router.get(
    "/{student_id}/photo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
    summary="The student's photo (JPEG)",
)
async def get_student_photo(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    user: CurrentUser,
) -> Response:
    photo = await service.get_photo(student_id)
    # Personal data: private cache only. Clients add ?v=<photo_version>, so a
    # changed photo gets a new URL and a long max-age is safe.
    return Response(
        content=photo.data,
        media_type=photo.content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.put("/{student_id}/photo", response_model=StudentRead, summary="Set or replace the student's photo")
async def set_student_photo(
    student_id: UUID,
    file: Annotated[UploadFile, File(description="JPG, PNG or WebP")],
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentRead:
    return await service.read(await service.set_photo(student_id, await _read_upload(file)))


@router.delete("/{student_id}/photo", response_model=StudentRead, summary="Remove the student's photo")
async def delete_student_photo(
    student_id: UUID,
    service: Annotated[StudentService, Depends(get_student_service)],
    actor: RequireStaff,
) -> StudentRead:
    return await service.read(await service.delete_photo(student_id))
