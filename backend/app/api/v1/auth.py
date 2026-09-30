"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, RequestMeta
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordChange,
    RefreshRequest,
    TokenPair,
    UserRead,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Sign in and receive an access/refresh token pair",
)
async def login(
    payload: LoginRequest, session: DbSession, request_meta: RequestMeta
) -> LoginResponse:
    return await AuthService(session).login(payload, request_meta)


@router.post("/refresh", response_model=TokenPair, summary="Exchange a refresh token")
async def refresh(payload: RefreshRequest, session: DbSession) -> TokenPair:
    return await AuthService(session).refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse, summary="Revoke the current refresh token")
async def logout(
    payload: RefreshRequest,
    session: DbSession,
    user: CurrentUser,
) -> MessageResponse:
    await AuthService(session).logout(payload.refresh_token, user)
    return MessageResponse(message="Signed out successfully.")


@router.post("/logout-all", response_model=MessageResponse, summary="Revoke every refresh token")
async def logout_all(session: DbSession, user: CurrentUser) -> MessageResponse:
    count = await AuthService(session).logout_all(user)
    return MessageResponse(message=f"Revoked {count} session(s).")


@router.get("/me", response_model=UserRead, summary="Current user profile")
async def me(session: DbSession, user: CurrentUser) -> UserRead:
    return UserRead.from_entity(user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change your own password",
)
async def change_password(
    payload: PasswordChange, session: DbSession, user: CurrentUser
) -> MessageResponse:
    await AuthService(session).change_password(user, payload.current_password, payload.new_password)
    await session.commit()
    return MessageResponse(message="Password updated. Please sign in again.")


@router.get(
    "/permissions",
    summary="Capabilities of the signed-in user (used by the UI to hide actions)",
)
async def permissions(user: CurrentUser) -> dict[str, object]:
    from app.core.security import ROLE_ORDER

    level = 99 if user.is_superuser else ROLE_ORDER.get(user.role, 0)
    return {
        "role": user.role,
        "level": level,
        "can_create_reports": level >= 20,
        "can_edit_reports": level >= 20,
        "can_delete_reports": level >= 30,
        "can_manage_users": level >= 40,
        "can_manage_settings": level >= 40,
        "can_backup": level >= 50,
        "can_view_audit": level >= 30,
    }
