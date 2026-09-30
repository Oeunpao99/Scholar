"""Authentication and user schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AliasChoices, EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import Password, SchemaBase, Username


class LoginRequest(SchemaBase):
    """Credentials. Users may sign in with either their username or email."""

    login: str = Field(
        min_length=3,
        max_length=255,
        validation_alias=AliasChoices("login", "username", "email"),
        description="Username or email address.",
        examples=["admin"],
    )
    password: str = Field(min_length=6, max_length=128, examples=["ChangeMe123!"])


class RefreshRequest(SchemaBase):
    refresh_token: str


class TokenPair(SchemaBase):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserBase(SchemaBase):
    email: str = Field(
        ...,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="User email address.",
        examples=["admin@scholar.local"],
    )
    username: Username
    full_name: str | None = None
    role: UserRole = UserRole.STAFF
    phone: str | None = None
    telegram_chat_id: str | None = None
    note: str | None = None


class UserCreate(UserBase):
    password: Password
    is_active: bool = True


class UserUpdate(SchemaBase):
    email: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
    )
    full_name: str | None = None
    role: UserRole | None = None
    phone: str | None = None
    telegram_chat_id: str | None = None
    note: str | None = None
    is_active: bool | None = None


class PasswordChange(SchemaBase):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: Password


class PasswordReset(SchemaBase):
    new_password: Password


class UserRead(UserBase):
    id: uuid.UUID
    is_active: bool
    is_superuser: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_entity(cls, user: object) -> UserRead:
        data = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "phone": getattr(user, "phone", None),
            "telegram_chat_id": getattr(user, "telegram_chat_id", None),
            "note": getattr(user, "note", None),
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        return cls(**data)  # type: ignore[arg-type]


class LoginResponse(SchemaBase):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
