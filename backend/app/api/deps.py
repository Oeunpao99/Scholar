"""FastAPI dependency providers (auth, RBAC, pagination, service injection)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.pagination import PageParams, local_today
from app.core.security import Role
from app.db.session import DbSession
from app.models.user import User
from app.services.ai.service import AIExtractionService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.cumulative_service import CumulativeService
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService
from app.services.report_service import DailyReportService
from app.services.settings_service import SettingsService
from app.services.telegram_service import TelegramReportService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

CREDENTIALS_ERROR = AuthenticationError("Provide a bearer token to access this resource.")


# --------------------------------------------------------------------- auth
async def get_current_user(
    session: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR
    return await AuthService(session).authenticate_token(credentials.credentials)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(role: str) -> Callable[..., User]:
    """Dependency factory enforcing a minimum role."""

    async def _dependency(user: CurrentUser) -> User:
        if user.is_superuser:
            return user
        from app.core.security import has_at_least

        if not has_at_least(user.role, role):
            raise PermissionDeniedError(
                f"This action requires the '{role}' role or higher (you are '{user.role}')."
            )
        return user

    return _dependency


RequireAdmin = Annotated[User, Depends(require_role(Role.ADMIN))]
RequireManager = Annotated[User, Depends(require_role(Role.MANAGER))]
RequireStaff = Annotated[User, Depends(require_role(Role.STAFF))]
RequireSuperadmin = Annotated[User, Depends(require_role(Role.SUPERADMIN))]


# ------------------------------------------------------------- request meta
def get_request_meta(request: Request) -> dict[str, Any]:
    return {
        "ip": request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        "user_agent": request.headers.get("user-agent"),
        "path": str(request.url.path),
    }


RequestMeta = Annotated[dict, Depends(get_request_meta)]


# --------------------------------------------------------------- pagination
def pagination_params(
    page: Annotated[int, Query(ge=1, le=10_000, description="1-based page number")] = 1,
    size: Annotated[int, Query(ge=1, le=200, description="Items per page")] = 20,
) -> PageParams:
    return PageParams(page=page, size=size)


Pagination = Annotated[PageParams, Depends(pagination_params)]

DateQuery = Annotated[date, Query(description="Report date (YYYY-MM-DD)")]


# ---------------------------------------------------------------- services
def get_audit_service(session: DbSession) -> AuditService:
    return AuditService(session)


def get_settings_service(session: DbSession) -> SettingsService:
    return SettingsService(session)


def get_cumulative_service(session: DbSession) -> CumulativeService:
    return CumulativeService(session)


def get_report_service(session: DbSession, user: CurrentUser) -> DailyReportService:
    return DailyReportService(session, user)


def get_dashboard_service(session: DbSession) -> DashboardService:
    return DashboardService(session)


def get_telegram_service(session: DbSession, user: CurrentUser) -> TelegramReportService:
    return TelegramReportService(session, user)


def get_export_service(session: DbSession, user: CurrentUser) -> ExportService:
    return ExportService(session, user)


def get_user_service(session: DbSession, user: CurrentUser) -> UserService:
    return UserService(session, user)


def get_ai_service(session: DbSession, user: CurrentUser) -> AIExtractionService:
    return AIExtractionService(session, user)


def get_backup_service(user: CurrentUser) -> BackupService:
    return BackupService(user)


# ------------------------------------------------------------------ extras
def optional_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"'{value}' is not a valid identifier.") from exc


def today() -> date:
    return local_today()


__all__ = [
    "CurrentUser",
    "RequireAdmin",
    "RequireManager",
    "RequireStaff",
    "RequireSuperadmin",
    "Pagination",
    "RequestMeta",
    "DbSession",
    "get_audit_service",
    "get_settings_service",
    "get_report_service",
    "get_dashboard_service",
    "get_telegram_service",
    "get_export_service",
    "get_user_service",
    "get_ai_service",
    "get_backup_service",
    "get_cumulative_service",
    "today",
    "optional_uuid",
]
