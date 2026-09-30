"""AI extraction endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, RequireStaff, get_ai_service
from app.schemas.ai import AIParseRequest, AIParseResponse, ApplyExtraction
from app.services.ai.service import SAMPLE_TEXT, AIExtractionService

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


@router.get(
    "/capabilities",
    summary="Which extraction providers are available on this deployment",
)
async def capabilities(
    service: Annotated[AIExtractionService, Depends(get_ai_service)],
    user: CurrentUser,
) -> dict[str, object]:
    return {
        "builtin": True,
        "llm": service.llm.configured,
        "ocr": service.ocr.available,
        "model": service.llm.name if service.llm.configured else None,
        "languages": ["km", "en"],
    }


@router.get("/sample", summary="Example text used by the AI page")
async def sample(user: CurrentUser) -> dict[str, str]:
    return {"text": SAMPLE_TEXT}


@router.post(
    "/parse",
    response_model=AIParseResponse,
    summary="Turn unstructured Khmer/English text into structured report data",
)
async def parse(
    payload: AIParseRequest,
    service: Annotated[AIExtractionService, Depends(get_ai_service)],
    actor: RequireStaff,
) -> AIParseResponse:
    return await service.parse(payload)


@router.post(
    "/apply",
    summary="Save a reviewed extraction as daily report(s)",
    status_code=status.HTTP_200_OK,
)
async def apply(
    payload: ApplyExtraction,
    service: Annotated[AIExtractionService, Depends(get_ai_service)],
    actor: RequireStaff,
) -> dict[str, object]:
    return await service.apply(payload)
