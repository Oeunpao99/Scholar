"""Administrative operations: backup, restore and system health."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.api.deps import CurrentUser, RequireAdmin, RequireSuperadmin, get_backup_service
from app.schemas.admin import BackupInfoRead, HealthRead, RestoreResult
from app.schemas.common import MessageResponse
from app.services.backup_service import BackupService

router = APIRouter(prefix="/admin", tags=["Administration"])


def _to_read(info: object) -> BackupInfoRead:
    return BackupInfoRead(
        filename=info.filename,  # type: ignore[attr-defined]
        size_bytes=info.size_bytes,  # type: ignore[attr-defined]
        size_display=info.size_display,  # type: ignore[attr-defined]
        created_at=info.created_at,  # type: ignore[attr-defined]
        format=info.format,  # type: ignore[attr-defined]
    )


@router.get("/backups", response_model=list[BackupInfoRead], summary="List database backups")
async def list_backups(
    service: Annotated[BackupService, Depends(get_backup_service)],
    actor: RequireAdmin,
) -> list[BackupInfoRead]:
    return [_to_read(info) for info in service.list_backups()]


@router.post(
    "/backups",
    response_model=BackupInfoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a database backup",
)
async def create_backup(
    service: Annotated[BackupService, Depends(get_backup_service)],
    actor: RequireAdmin,
    format: Annotated[
        str, Query(alias="format", pattern="^(custom|plain|tar|directory)$")
    ] = "custom",
) -> BackupInfoRead:
    return _to_read(await service.create(format))


@router.get(
    "/backups/{filename}",
    summary="Download a backup file",
    response_class=Response,
)
async def download_backup(
    filename: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
    actor: RequireAdmin,
) -> Response:
    payload = service.read(filename)
    return Response(
        content=payload,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/backups/{filename}/restore",
    response_model=RestoreResult,
    summary="Restore the database from a backup (superadmin only)",
)
async def restore_backup(
    filename: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
    actor: RequireSuperadmin,
    clean: bool = True,
) -> RestoreResult:
    result = await service.restore(filename, clean=clean, actor=actor)
    return RestoreResult(**result)  # type: ignore[arg-type]


@router.delete(
    "/backups/{filename}", response_model=MessageResponse, summary="Delete a backup"
)
async def delete_backup(
    filename: str,
    service: Annotated[BackupService, Depends(get_backup_service)],
    actor: RequireSuperadmin,
) -> MessageResponse:
    await service.delete(filename, actor)
    return MessageResponse(message=f"Deleted {filename}.")


@router.get("/health", response_model=HealthRead, summary="System health snapshot")
async def health(
    service: Annotated[BackupService, Depends(get_backup_service)],
    user: CurrentUser,
) -> HealthRead:
    from app.core.config import settings

    return HealthRead(
        status="ok",
        environment=settings.ENVIRONMENT,
        server_time=datetime.now(UTC).isoformat(),
        timezone=settings.REPORTS_TIMEZONE,
        backup_dir=str(settings.BACKUP_DIR),
    )
