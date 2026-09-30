"""Telegram report assembly and delivery."""

from __future__ import annotations

import base64
import logging
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, NotFoundError, ValidationError
from app.models.enums import SettingKey
from app.models.user import User
from app.repositories.reference_repo import CategoryRepository
from app.repositories.report_repo import DailyReportRepository
from app.schemas.analytics import TelegramMessage
from app.schemas.common import Counters
from app.services.audit_service import AuditService
from app.services.cumulative_service import GRADES, CumulativeService
from app.services.settings_service import SettingsService
from app.services.telegram_generator import TelegramReportGenerator

logger = logging.getLogger("scholar.telegram.service")

TELEGRAM_API = "https://api.telegram.org"


class TelegramReportService:
    """Builds the daily Khmer message and optionally sends it to Telegram."""

    def __init__(self, session: AsyncSession, current_user: User | None = None) -> None:
        self.session = session
        self.current_user = current_user
        self.repo = DailyReportRepository(session)
        self.category_repo = CategoryRepository(session)
        self.cumulative = CumulativeService(session)
        self.settings = SettingsService(session)
        self.audit = AuditService(session)

    # ---------------------------------------------------------------- build
    async def build_message(
        self,
        report_date: date,
        *,
        zero_pad: bool = True,
        include_today_grades: bool = True,
        include_grand_total: bool = False,
        include_empty_categories: bool = True,
        grades: list[str] | None = None,
    ) -> str:
        selected = normalize_grades(grades)
        filtered = selected != GRADES
        year = await self.settings.get_current_year()
        categories = await self.category_repo.list_ordered()
        reports = {str(r.category_id): r for r in await self.repo.list_by_date(report_date)}
        cumulative = await self.cumulative.cumulative_by_category(report_date)

        blocks: list[dict] = []
        for category in categories:
            report = reports.get(str(category.id))
            today_grades: dict[str, Counters] = {}
            if report is not None:
                for entry in report.entries:
                    today_grades[entry.grade] = Counters(
                        total=entry.today_total,
                        female=entry.today_female,
                        pp=entry.today_pp,
                        kp=entry.today_kp,
                    )
                for grade in GRADES:
                    today_grades.setdefault(grade, Counters())

            cum = next(
                (c for c in cumulative if c.category_id == str(category.id)),
                None,
            )
            if cum is None:
                cum_counts = Counters()
            elif filtered:
                cum_counts = _sum_counters([cum.grade_counters(g) for g in selected])
            else:
                cum_counts = cum.counters()
            if filtered:
                today_grades = {g: c for g, c in today_grades.items() if g in selected}
            blocks.append(
                {
                    "roman_numeral": category.roman_numeral or f"{category.position}.",
                    "title": category.render_title(year),
                    "today_grades": today_grades,
                    "cumulative": cum_counts,
                }
            )

        grand_total = _sum_counters([b["cumulative"] for b in blocks])

        generator = TelegramReportGenerator(
            zero_pad=zero_pad,
            include_today_grades=include_today_grades,
            include_grand_total=include_grand_total,
            include_empty_categories=include_empty_categories,
            all_grades=selected,
        )
        return generator.render(
            report_date=report_date, categories=blocks, grand_total=grand_total
        )

    async def preview(self, report_date: date, **options) -> TelegramMessage:
        text = await self.build_message(report_date, **options)
        return TelegramMessage(report_date=report_date, text=text, sent=False)

    async def preview_for_payload(
        self,
        report_date: date,
        *,
        include_today_grades: bool = True,
        include_grand_total: bool = False,
        include_empty_categories: bool = True,
        zero_pad: bool = True,
        grades: list[str] | None = None,
    ) -> TelegramMessage:
        return TelegramMessage(
            report_date=report_date,
            text=await self.build_message(
                report_date,
                zero_pad=zero_pad,
                include_today_grades=include_today_grades,
                include_grand_total=include_grand_total,
                include_empty_categories=include_empty_categories,
                grades=grades,
            ),
            sent=False,
        )

    async def build_category_message(
        self, report_date: date, category_code: str, *, zero_pad: bool = True
    ) -> str:
        """Single-category variant, handy for per-channel broadcasts."""
        category = await self.category_repo.get_by_code(category_code)
        if category is None:
            raise NotFoundError(f"Unknown category: {category_code}")
        full = await self.build_message(
            report_date,
            include_empty_categories=False,
            include_today_grades=True,
        )
        return full  # full text keeps the mandated section ordering

    # ------------------------------------------------------------------ send
    async def send(
        self,
        report_date: date,
        *,
        chat_id: str | None = None,
        dry_run: bool = False,
        include_today_grades: bool = True,
        include_grand_total: bool = False,
        include_empty_categories: bool = True,
        zero_pad: bool = True,
        grades: list[str] | None = None,
    ) -> TelegramMessage:
        # Same options as the preview, so what is sent matches what was shown.
        text = await self.build_message(
            report_date,
            zero_pad=zero_pad,
            include_today_grades=include_today_grades,
            include_grand_total=include_grand_total,
            include_empty_categories=include_empty_categories,
            grades=grades,
        )
        target = chat_id or await self._default_chat_id()
        if dry_run:
            return TelegramMessage(report_date=report_date, text=text, sent=False)
        if not target:
            raise ValidationError(
                "No Telegram chat configured. Provide chat_id or set the telegram_chat_id setting."
            )
        message_id = await self._post_message(target, text)
        await self.audit.log(
            action="send",
            entity_type="telegram",
            entity_id=str(report_date),
            summary=f"Sent Telegram report for {report_date} to {target}",
            user=self.current_user,
        )
        return TelegramMessage(
            report_date=report_date, text=text, sent=True, message_id=message_id
        )

    async def _post_message(self, chat_id: str, text: str) -> int | None:
        token = await self._bot_token()
        if not token:
            raise ValidationError("Telegram bot token is not configured.")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{TELEGRAM_API}/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": ""},
            )
        if response.status_code >= 400:
            raise AppError(
                f"Telegram rejected the message (HTTP {response.status_code}).",
                status_code=502,
                code="telegram_error",
            )
        return int(response.json().get("result", {}).get("message_id", 0)) or None

    async def _bot_token(self) -> str | None:
        return (await self.settings.get(SettingKey.TELEGRAM_BOT_TOKEN)) or settings.__dict__.get(
            "TELEGRAM_BOT_TOKEN"
        )

    async def _default_chat_id(self) -> str | None:
        chat_id = await self.settings.get(SettingKey.TELEGRAM_CHAT_ID)
        if chat_id:
            return chat_id
        if self.current_user and self.current_user.telegram_chat_id:
            return self.current_user.telegram_chat_id
        return None

    async def verify_bot(self) -> dict[str, object]:
        # An unset token is a normal state (bot not set up yet), not a bad
        # request — report it so the UI can show "offline" without an error.
        token = await self._bot_token()
        if not token:
            return {"ok": False, "configured": False, "message": "Telegram bot token is not configured."}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{TELEGRAM_API}/bot{token}/getMe")
        except httpx.HTTPError as exc:
            return {"ok": False, "configured": True, "message": f"Could not reach Telegram: {exc}"}
        body = response.json() if response.content else {}
        bot = body.get("result") or {}
        return {
            "ok": response.is_success,
            "configured": True,
            "status": response.status_code,
            "username": bot.get("username"),
            "first_name": bot.get("first_name"),
            "body": body,
        }


def normalize_grades(grades: list[str] | None) -> tuple[str, ...]:
    """Valid grades in A-E order; nothing (or nothing valid) means all grades."""
    wanted = {g.strip().upper() for g in grades or []}
    selected = tuple(g for g in GRADES if g in wanted)
    return selected or tuple(GRADES)


def _sum_counters(items: list[Counters]) -> Counters:
    return Counters(
        total=sum(i.total for i in items),
        female=sum(i.female for i in items),
        pp=sum(i.pp for i in items),
        kp=sum(i.kp for i in items),
    )


def decode_base64_image(payload: str) -> bytes:
    """Helper for clients that upload base64 images to the OCR endpoint."""
    if "," in payload and payload.strip().startswith("data:"):
        payload = payload.split(",", 1)[1]
    return base64.b64decode(payload)
