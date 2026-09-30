"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import engine

logger = logging.getLogger("scholar.main")

DESCRIPTION = """
**Scholar** - daily student enrollment management.

Staff record only *today's gain*; every cumulative total, the Khmer Telegram
report, the dashboard and the exports are derived from that ledger.

* **Auth** - `POST /api/v1/auth/login` returns an access token.
* **RBAC** - `superadmin` > `admin` > `manager` > `staff` > `viewer`.
* **Docs** - interactive documentation is available at `/docs`.
"""

TAGS_METADATA = [
    {"name": "Authentication", "description": "Sign in, refresh tokens and profile."},
    {"name": "Daily Reports", "description": "Record today's gain per category and grade."},
    {"name": "Dashboard", "description": "Aggregated metrics, trends and activities."},
    {"name": "Telegram", "description": "Khmer daily report rendering and delivery."},
    {"name": "Export", "description": "CSV, Excel and PDF exports."},
    {"name": "AI Assistant", "description": "Extract structured data from unstructured text."},
    {"name": "Users", "description": "User administration."},
    {"name": "Settings & Reference Data", "description": "Year, categories and grades."},
    {"name": "Audit Logs", "description": "Every change, who made it and when."},
    {"name": "Administration", "description": "Backup, restore and health."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    logger.info("Starting %s (%s)", settings.PROJECT_NAME, settings.ENVIRONMENT)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as exc:  # noqa: BLE001 - the API still boots for health checks
        logger.error("Database is not reachable: %s", exc)
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": True, "docExpansion": "none"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Row-Count"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Health"], summary="Service banner")
    async def root() -> dict[str, str]:
        return {
            "service": settings.PROJECT_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api": settings.API_V1_PREFIX,
        }

    @app.get("/health", tags=["Health"], summary="Liveness and database probe")
    @app.get("/api/v1/health", tags=["Health"], summary="Liveness and database probe")
    async def health_check() -> JSONResponse:
        database_ok = True
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            database_ok = False
        code = status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(
            status_code=code,
            content={"status": "ok" if database_ok else "degraded", "database": database_ok},
        )

    @app.get("/api/v1/meta", tags=["Health"], summary="Client bootstrap metadata")
    async def meta() -> dict[str, object]:
        return {
            "current_year": await _current_year(),
            "grades": ["A", "B", "C", "D", "E"],
            "categories": [
                {"code": "current_year", "position": 1},
                {"code": "before_current_year", "position": 2},
                {"code": "other_province", "position": 3},
            ],
        }

    return app


async def _current_year() -> int:
    from app.db.session import SessionLocal
    from app.services.settings_service import SettingsService

    try:
        async with SessionLocal() as session:
            return await SettingsService(session).get_current_year()
    except Exception:  # noqa: BLE001
        return settings.DEFAULT_CURRENT_YEAR


app = create_app()
