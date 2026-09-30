"""Application-wide exception hierarchy and handlers."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.config import settings

logger = logging.getLogger("scholar.errors")

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", None) or getattr(
    status, "HTTP_422_UNPROCESSABLE_ENTITY", 422
)


class AppError(Exception):
    """Base class for every domain error raised by the service layer."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"
    message: str = "Application error."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Resource already exists."


class ValidationError(AppError):
    status_code = HTTP_422_UNPROCESSABLE
    code = "validation_error"
    message = "Validation failed."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"
    message = "Invalid or missing credentials."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"
    message = "You do not have permission to perform this action."


class ImmutableRecordError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "immutable_record"
    message = "This record can no longer be modified."


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "rate_limited"
    message = "Too many requests. Please slow down."


def _payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers so clients always receive the same envelope."""

    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.exception("Unhandled application error: %s", exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
            headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        from fastapi.encoders import jsonable_encoder

        return JSONResponse(
            status_code=HTTP_422_UNPROCESSABLE,
            content=_payload("validation_error", "Request validation failed.", {"errors": jsonable_encoder(exc.errors())}),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Database integrity error: %s", exc)
        message = "The operation conflicts with existing data."
        if settings.DEBUG:
            message = f"{message} ({exc.orig})"
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_payload("integrity_error", message),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _sqlalchemy_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_payload("database_error", "A database error occurred."),
        )
