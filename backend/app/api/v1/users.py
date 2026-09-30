"""User administration endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, Pagination, RequireAdmin, get_user_service
from app.models.enums import UserRole
from app.schemas.auth import PasswordReset, UserCreate, UserRead, UserUpdate
from app.schemas.common import MessageResponse, Page
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserRead], summary="List users")
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
    pagination: Pagination,
    q: Annotated[str | None, Query(max_length=120)] = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> Page[UserRead]:
    page = await service.list(
        page=pagination.page, size=pagination.size, q=q,
        role=role.value if role else None, is_active=is_active,
    )
    return Page(items=[UserRead.from_entity(u) for u in page.items], meta=page.meta)


@router.get("/stats", summary="User counts by role")
async def stats(
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> dict[str, int]:
    return await service.stats()


@router.get("/roles", summary="Available roles with their privilege level")
async def roles(actor: RequireAdmin) -> list[dict[str, object]]:
    from app.core.security import ROLE_ORDER

    return [
        {"value": role, "level": level}
        for role, level in sorted(ROLE_ORDER.items(), key=lambda item: item[1], reverse=True)
    ]


@router.get("/{user_id}", response_model=UserRead, summary="Fetch a user")
async def get_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> UserRead:
    return UserRead.from_entity(await service.get(user_id))


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> UserRead:
    return UserRead.from_entity(await service.create(payload))


@router.patch("/{user_id}", response_model=UserRead, summary="Update a user")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> UserRead:
    return UserRead.from_entity(await service.update(user_id, payload))


@router.post(
    "/{user_id}/activate",
    response_model=UserRead,
    summary="Activate or deactivate a user",
)
async def set_active(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
    is_active: bool = True,
) -> UserRead:
    return UserRead.from_entity(await service.set_active(user_id, is_active))


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    summary="Reset a user's password",
)
async def reset_password(
    user_id: UUID,
    payload: PasswordReset,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> MessageResponse:
    await service.reset_password(user_id, payload.new_password)
    return MessageResponse(message="Password reset. All sessions were revoked.")


@router.delete("/{user_id}", response_model=MessageResponse, summary="Delete a user")
async def delete_user(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    actor: RequireAdmin,
) -> MessageResponse:
    await service.delete(user_id)
    return MessageResponse(message="User deleted.")
