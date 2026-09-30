"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import admin, ai, audit, auth, dashboard, exports, references, reports, settings, telegram, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(references.router)
api_router.include_router(reports.router)
api_router.include_router(dashboard.router)
api_router.include_router(telegram.router)
api_router.include_router(exports.router)
api_router.include_router(ai.router)
api_router.include_router(users.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
