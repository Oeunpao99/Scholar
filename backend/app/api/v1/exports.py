"""Export endpoints (CSV / Excel / PDF / Telegram text)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import CurrentUser, RequireStaff, get_export_service
from app.schemas.analytics import ExportRequest
from app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["Export"])


@router.get("/formats", summary="Available export formats")
async def formats(user: CurrentUser) -> list[dict[str, str]]:
    return [
        {"value": "csv", "label": "CSV", "mime": "text/csv"},
        {"value": "excel", "label": "Excel (.xlsx)", "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        {"value": "pdf", "label": "PDF", "mime": "application/pdf"},
        {"value": "telegram", "label": "Telegram text", "mime": "text/plain"},
    ]


@router.post(
    "/{fmt}",
    summary="Export the daily report data",
    response_class=Response,
    responses={
        200: {
            "description": "The generated file",
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
                "application/pdf": {},
                "text/plain": {},
            },
        }
    },
)
async def export(
    fmt: str,
    request: ExportRequest,
    service: Annotated[ExportService, Depends(get_export_service)],
    actor: RequireStaff,
) -> Response:
    if fmt == "telegram":
        payload, filename, media = await service.export_telegram_text(request)
    else:
        request = request.model_copy(update={"format": fmt})
        payload, filename, media = await service.export(request)

    disposition = "attachment" if fmt != "telegram" else "inline"
    return Response(
        content=payload,
        media_type=media,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "X-Row-Count": str(payload.count(b"\n")),
        },
    )
