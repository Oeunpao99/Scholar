"""
AI extraction orchestrator.

Pipeline:  raw text (+ optional screenshots)
              -> OCR (when images are attached)
              -> built-in parser  ->  optional LLM pass-through / fallback
              -> validated :class:`ExtractedReport` for human review
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.models.enums import AuditAction
from app.models.user import User
from app.repositories.reference_repo import CategoryRepository
from app.schemas.ai import (
    AIParseRequest,
    AIParseResponse,
    ApplyExtraction,
    ExtractedReport,
)
from app.schemas.common import Counters
from app.schemas.report import DailyReportCreate, GradeEntryInput
from app.services.ai.builtin_extractor import BuiltinExtractor
from app.services.ai.llm_extractor import LlmExtractor
from app.services.ai.ocr import OcrService
from app.services.audit_service import AuditService
from app.services.report_service import DailyReportService
from app.services.settings_service import SettingsService
from app.services.telegram_generator import TelegramReportGenerator

logger = logging.getLogger("scholar.ai")

SUPPORTED_PROVIDERS = {"builtin", "llm", "ocr", "llm+ocr"}

SAMPLE_TEXT = (
    "29/09/2026\n\n"
    "I. បានទទួលពាក្យបាក់ឌុបឆ្នាំ2026\n"
    "-និទ្ទេស D ចំនួន : 01 នាក់ ស្រី 00 នាក់\n"
    "(PP: 01 នាក់ , KP: 00 នាក់)\n"
    "សរុបរួមចំនួន : 12 នាក់ ស្រី 05 នាក់\n"
    "(PP: 08 នាក់, KP: 04 នាក់)\n\n"
    "II. បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ2026\n"
    "-និទ្ទេស C ចំនួន : 02 នាក់ ស្រី 01 នាក់\n"
    "(PP: 01 នាក់ , KP: 01 នាក់)\n"
)


@dataclass(slots=True)
class ExtractedCategorySummary:
    """Display metadata used by the dry-run preview."""

    category_code: str
    category_title: str


class AIExtractionService:
    def __init__(self, session: AsyncSession, current_user: User | None = None) -> None:
        self.session = session
        self.current_user = current_user
        self.builtin = BuiltinExtractor()
        self.llm = LlmExtractor()
        self.ocr = OcrService()
        self.settings = SettingsService(session)
        self.categories = CategoryRepository(session)
        self.audit = AuditService(session)

    # ---------------------------------------------------------------- parse
    async def parse(self, request: AIParseRequest) -> AIParseResponse:
        provider = request.effective_provider
        if provider not in SUPPORTED_PROVIDERS:
            raise ValidationError(
                f"Unsupported provider '{provider}'. Use one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}."
            )
        year = request.current_year or await self.settings.get_current_year()

        ocr_text: str | None = None
        if request.images:
            ocr_text = self.ocr.extract_text(request.images)
            if not ocr_text.strip():
                raise ValidationError("មិនអាចអានអត្ថបទពីរូបភាពបានទេ — សូមប្រើរូបភាពច្បាស់ជាងនេះ។")

        # Whatever the provider, text read from attached images is parsed too.
        text = f"{request.text}\n{ocr_text}".strip() if ocr_text else request.text

        warnings: list[str] = []
        extracted: ExtractedReport | None = None
        raw_response: str | None = None

        if provider in {"llm", "llm+ocr"} and self.llm.configured:
            try:
                extracted = self.llm.extract(
                    text,
                    default_date=request.default_date,
                    current_year=year,
                    ocr_text=ocr_text,
                    images=request.images,
                )
            except Exception as exc:  # noqa: BLE001 - fall back to the local parser
                logger.warning("LLM extraction failed, falling back to builtin: %s", exc)
                warnings.append(f"មិនអាចភ្ជាប់ទៅម៉ាស៊ីន AI បានទេ ({exc}) — បានប្រើការវិភាគមូលដ្ឋានជំនួស។")

        if extracted is None:
            extracted = self.builtin.extract(
                text, default_date=request.default_date, current_year=year
            )
        elif self.builtin.extract(text, default_date=request.default_date, current_year=year).warnings:
            warnings.extend(
                f"ការវិភាគមូលដ្ឋាន: {w}"
                for w in self.builtin.extract(
                    text, default_date=request.default_date, current_year=year
                ).warnings
            )

        if warnings:
            extracted = extracted.model_copy(update={"warnings": [*extracted.warnings, *warnings]})

        await self.audit.log(
            action=AuditAction.AI_PARSE,
            entity_type="ai_extraction",
            summary=f"AI extraction via {provider}: {len(extracted.categories)} categor(y/ies), "
            f"confidence {extracted.confidence}",
            changes={"provider": provider, "date": extracted.date.isoformat() if extracted.date else None},
            user=self.current_user,
        )
        await self.session.commit()

        return AIParseResponse(
            provider=provider,
            extracted=extracted,
            preview_text=await self._preview(extracted, year),
            ocr_text=ocr_text,
            raw_response=raw_response,
        )

    # ---------------------------------------------------------------- apply
    async def apply(self, payload: ApplyExtraction) -> dict[str, object]:
        """
        Persist a reviewed extraction.  With ``dry_run`` the payload is only
        validated and echoed back so the UI can preview the outcome.
        """
        if not payload.categories:
            raise ValidationError("គ្មានផ្នែកសម្រាប់រក្សាទុកទេ។")

        year = await self.settings.get_current_year()
        catalogue = {c.code: c for c in await self.categories.list_ordered()}
        service = DailyReportService(self.session, self.current_user)
        planned: list[DailyReportCreate] = []

        for extracted in payload.categories:
            category = catalogue.get(extracted.category)
            if category is None:
                raise NotFoundError(f"Unknown category code: {extracted.category}")
            grades = [
                GradeEntryInput(
                    grade=g.grade,  # type: ignore[arg-type]
                    total=g.total,
                    female=g.female,
                    pp=g.pp,
                    kp=g.kp,
                )
                for g in extracted.grades
            ]
            if grades:
                # The per-grade breakdown is the source of truth once present.
                total = sum(g.total for g in grades)
                female = sum(g.female for g in grades)
                pp = sum(g.pp for g in grades)
                kp = sum(g.kp for g in grades)
            else:
                total = extracted.total
                female = extracted.female
                pp = extracted.pp
                kp = extracted.kp
            planned.append(
                (
                    ExtractedCategorySummary(
                        category_code=extracted.category,
                        category_title=category.render_title(year),
                    ),
                    DailyReportCreate(
                        report_date=payload.report_date,
                        category_id=category.id,
                        grades=grades,
                        total=total,
                        female=female,
                        pp=pp,
                        kp=kp,
                        source="ai",
                    ),
                )
            )

        if payload.dry_run:
            return {
                "dry_run": True,
                "year": year,
                "reports": [
                    {
                        "category_code": entry.category_code,
                        "category_title": entry.category_title,
                        "total": plan.total,
                        "female": plan.female,
                        "pp": plan.pp,
                        "kp": plan.kp,
                        "grades": [g.model_dump(mode="json") for g in plan.grades],
                    }
                    for entry, plan in planned
                ],
            }

        saved = await service.bulk_create([plan for _, plan in planned])
        await self.session.commit()
        return {
            "dry_run": False,
            "created": [{"id": str(r.id), "date": r.report_date.isoformat()} for r in saved],
        }

    # -------------------------------------------------------------- preview
    async def _preview(self, extracted: ExtractedReport, year: int) -> str:
        """Render the extracted figures in the Telegram layout for a quick check."""
        blocks: list[dict] = []
        for item in extracted.categories:
            category = await self.categories.get_by_code(item.category)
            title = item.title or (category.render_title(year) if category else item.category)
            blocks.append(
                {
                    "roman_numeral": category.roman_numeral if category else "",
                    "title": title,
                    "today_grades": {
                        str(g.grade): Counters(total=g.total, female=g.female, pp=g.pp, kp=g.kp)
                        for g in item.grades
                    },
                    "cumulative": Counters(
                        total=item.total, female=item.female, pp=item.pp, kp=item.kp
                    ),
                }
            )
        if not blocks:
            return ""
        return TelegramReportGenerator().render(
            report_date=extracted.date or date.today(), categories=blocks
        )
