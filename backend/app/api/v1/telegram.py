"""Telegram report endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, RequireManager, get_telegram_service
from app.schemas.analytics import TelegramMessage, TelegramSendRequest
from app.services.telegram_service import TelegramReportService

router = APIRouter(prefix="/telegram", tags=["Telegram"])


@router.get(
    "/preview",
    response_model=TelegramMessage,
    summary="Render the Khmer report without sending it",
)
async def preview(
    service: Annotated[TelegramReportService, Depends(get_telegram_service)],
    user: CurrentUser,
    date_: Annotated[date | None, Query(alias="date", description="Target report date")] = None,
    report_date: date | None = None,
    include_today_grades: bool = True,
    include_grand_total: bool = False,
    include_empty_categories: bool = True,
    zero_pad: bool = True,
    grades: Annotated[
        list[str] | None,
        Query(max_length=5, description="Only report these grades (repeat: ?grades=A&grades=D); omit for all."),
    ] = None,
) -> TelegramMessage:
    from app.core.pagination import local_today

    target = date_ or report_date or local_today()
    return await service.preview_for_payload(
        target,
        include_today_grades=include_today_grades,
        include_grand_total=include_grand_total,
        include_empty_categories=include_empty_categories,
        zero_pad=zero_pad,
        grades=grades,
    )


@router.get(
    "/report/{report_date}",
    response_model=TelegramMessage,
    summary="Render the Khmer report for a specific date",
)
async def report_for_date(
    report_date: date,
    service: Annotated[TelegramReportService, Depends(get_telegram_service)],
    user: CurrentUser,
    zero_pad: Annotated[bool, Query(description="Two-digit zero padding")] = True,
) -> TelegramMessage:
    return TelegramMessage(
        report_date=report_date,
        text=await service.build_message(report_date, zero_pad=zero_pad),
        sent=False,
    )


@router.post(
    "/send",
    response_model=TelegramMessage,
    status_code=status.HTTP_200_OK,
    summary="Send the daily report to Telegram",
)
async def send(
    payload: TelegramSendRequest,
    service: Annotated[TelegramReportService, Depends(get_telegram_service)],
    actor: RequireManager,
) -> TelegramMessage:
    message = await service.send(
        payload.report_date,
        chat_id=payload.chat_id,
        dry_run=payload.dry_run,
        include_today_grades=payload.include_today_grades,
        include_grand_total=payload.include_grand_total,
        include_empty_categories=payload.include_empty_categories,
        zero_pad=payload.zero_pad,
        grades=payload.grades,
    )
    await service.session.commit()
    return message


@router.get(
    "/bot/verify",
    summary="Check that the configured bot token is valid",
)
async def verify_bot(
    service: Annotated[TelegramReportService, Depends(get_telegram_service)],
    actor: RequireManager,
) -> dict[str, object]:
    return await service.verify_bot()
