"""Password hashing, JWT issuance/verification and RBAC primitives."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import bcrypt
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"


class Role(StrEnum):
    """Role based access control levels."""

    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


# Ordered from most to least privileged.
ROLE_ORDER: dict[str, int] = {
    Role.VIEWER: 10,
    Role.STAFF: 20,
    Role.MANAGER: 30,
    Role.ADMIN: 40,
    Role.SUPERADMIN: 50,
}


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(raw_password, hashed_password)
    except (ValueError, TypeError, bcrypt.error):
        return False


def _create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str, *, role: str | None = None, username: str | None = None
) -> str:
    claims: dict[str, Any] = {}
    if role:
        claims["role"] = role
    if username:
        claims["username"] = username
    return _create_token(
        subject, ACCESS_TOKEN, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), claims
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, REFRESH_TOKEN, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def decode_token(token: str, *, expected_type: str | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises ``AuthenticationError`` when invalid."""
    from app.core.errors import AuthenticationError

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc.__class__.__name__}") from exc

    if expected_type and payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type.")
    if not payload.get("sub"):
        raise AuthenticationError("Token subject missing.")
    return payload


def has_at_least(role: str | None, required: str) -> bool:
    """Return True when ``role`` is at least as privileged as ``required``."""
    if role is None:
        return False
    if role == required:
        return True
    return ROLE_ORDER.get(role, 0) >= ROLE_ORDER.get(required, 99)


def token_expiry_seconds() -> int:
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
