"""Audit log endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUser, Pagination, get_audit_service
from app.models.enums import AuditAction
from app.schemas.audit import AuditLogRead
from app.schemas.common import Page
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=Page[AuditLogRead], summary="Browse the audit trail")
async def list_audit(
    service: Annotated[AuditService, Depends(get_audit_service)],
    user: CurrentUser,
    pagination: Pagination,
    user_id: UUID | None = None,
    action: AuditAction | None = None,
    entity_type: str | None = None,
    start: date | None = None,
    end: date | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> Page[AuditLogRead]:
    page = await service.list(
        page=pagination.page,
        size=pagination.size,
        user_id=user_id,
        action=action.value if action else None,
        entity_type=entity_type,
        start=start,
        end=end,
        q=q,
    )
    return Page(items=[AuditLogRead.model_validate(i) for i in page.items], meta=page.meta)


@router.get("/recent", response_model=list[AuditLogRead], summary="Most recent entries")
async def recent(
    service: Annotated[AuditService, Depends(get_audit_service)],
    user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[AuditLogRead]:
    return [AuditLogRead.model_validate(log) for log in await service.repo.recent(limit)]


@router.get("/actions", summary="Distinct action types present in the log")
async def actions(
    service: Annotated[AuditService, Depends(get_audit_service)],
    user: CurrentUser,
) -> list[str]:
    return list(await service.repo.distinct_actions())


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=list[AuditLogRead],
    summary="History for a specific record",
)
async def entity_history(
    entity_type: str,
    entity_id: str,
    service: Annotated[AuditService, Depends(get_audit_service)],
    user: CurrentUser,
) -> list[AuditLogRead]:
    logs = await service.history_for(entity_type, entity_id)
    return [AuditLogRead.model_validate(log) for log in logs]
