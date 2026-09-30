"""Authentication, token issuance and RBAC guards."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AuthenticationError, PermissionDeniedError, ValidationError
from app.core.security import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    has_at_least,
    hash_password,
    token_expiry_seconds,
    verify_password,
)
from app.models.enums import AuditAction
from app.models.user import RefreshToken, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, TokenPair, UserRead
from app.services.audit_service import AuditService

logger = logging.getLogger("scholar.auth")


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.audit = AuditService(session)

    # ---------------------------------------------------------------- login
    async def login(
        self, payload: LoginRequest, request_meta: dict[str, Any] | None = None
    ) -> LoginResponse:
        user = await self.repo.get_optional_by_identifier(payload.login)
        if user is None or not verify_password(payload.password, user.hashed_password):
            await self.audit.log(
                action=AuditAction.LOGIN,
                entity_type="user",
                entity_id=str(payload.login),
                summary="Failed login attempt",
                request_meta=request_meta,
            )
            raise AuthenticationError("Incorrect username or password.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")

        user.last_login_at = datetime.now(UTC)
        tokens = await self._issue_tokens(user, request_meta)
        await self.audit.log(
            action=AuditAction.LOGIN,
            entity_type="user",
            entity_id=user.id,
            summary=f"{user.username} signed in",
            user=user,
            request_meta=request_meta,
        )
        await self.session.commit()
        return LoginResponse(**tokens.model_dump(), user=UserRead.from_entity(user))

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN)
        user_id = UUID(payload["sub"])
        stored = await self.repo.refresh_tokens.get_valid(refresh_token, datetime.now(UTC))
        if stored is None:
            raise AuthenticationError("Refresh token is expired or revoked.")
        user = await self.repo.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is unavailable.")
        access = create_access_token(str(user.id), role=user.role, username=user.username)
        return TokenPair(
            access_token=access,
            refresh_token=refresh_token,
            expires_in=token_expiry_seconds(),
        )

    async def logout(self, refresh_token: str, user: User | None = None) -> None:
        stored = await self.repo.refresh_tokens.get_by(token=refresh_token)
        if stored:
            stored.revoked_at = datetime.now(UTC)
        await self.audit.log(
            action=AuditAction.LOGOUT,
            entity_type="user",
            entity_id=str(user.id) if user else None,
            summary="Signed out",
            user=user,
        )
        await self.session.commit()

    async def logout_all(self, user: User) -> int:
        count = await self.repo.refresh_tokens.revoke_for_user(user.id, datetime.now(UTC))
        await self.session.commit()
        return count

    # ------------------------------------------------------------- identity
    async def authenticate_token(self, token: str) -> User:
        payload = decode_token(token, expected_type=ACCESS_TOKEN)
        try:
            user_id = UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("Malformed token subject.") from exc
        user = await self.repo.get(user_id)
        if user is None:
            raise AuthenticationError("User no longer exists.")
        if not user.is_active:
            raise AuthenticationError("This account is disabled.")
        return user

    # -------------------------------------------------------------- helpers
    async def _issue_tokens(
        self, user: User, request_meta: dict[str, Any] | None = None
    ) -> TokenPair:
        access = create_access_token(str(user.id), role=user.role, username=user.username)
        refresh = create_refresh_token(str(user.id))
        record = RefreshToken(
            user_id=user.id,
            token=refresh,
            expires_at=datetime.fromtimestamp(
                decode_token(refresh, expected_type=REFRESH_TOKEN)["exp"], tz=UTC
            ),
            user_agent=(request_meta or {}).get("user_agent"),
            ip_address=(request_meta or {}).get("ip"),
        )
        self.repo.refresh_tokens.add(record)
        await self.session.flush()
        return TokenPair(
            access_token=access, refresh_token=refresh, expires_in=token_expiry_seconds()
        )

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise AuthenticationError("Current password is incorrect.")
        self._validate_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = datetime.now(UTC)
        await self.repo.refresh_tokens.revoke_for_user(user.id, datetime.now(UTC))
        await self.session.flush()

    async def reset_password(self, user: User, new_password: str, actor: User) -> None:
        self._validate_password_strength(new_password)
        user.hashed_password = hash_password(new_password)
        user.password_changed_at = datetime.now(UTC)
        await self.repo.refresh_tokens.revoke_for_user(user.id, datetime.now(UTC))
        await self.audit.log(
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            summary=f"Password reset for {user.username} by {actor.username}",
            user=actor,
        )
        await self.session.flush()

    @staticmethod
    def _validate_password_strength(password: str) -> None:
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long."
            )
        if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
            raise ValidationError("Password must contain both letters and digits.")

    @staticmethod
    def authorize(user: User | None, required_role: str) -> None:
        if user is None:
            raise AuthenticationError()
        if user.is_superuser or has_at_least(user.role, required_role):
            return
        raise PermissionDeniedError(
            f"This action requires the '{required_role}' role or higher."
        )

    @staticmethod
    def can_edit_reports(user: User | None) -> bool:
        return user is not None and (user.is_superuser or has_at_least(user.role, Role.STAFF))

    @staticmethod
    def can_delete_reports(user: User | None) -> bool:
        return user is not None and (user.is_superuser or has_at_least(user.role, Role.MANAGER))
