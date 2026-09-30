"""System settings service (current year, institution name, telegram config)."""

from __future__ import annotations

import logging
import uuid
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings as env_settings
from app.models.enums import SettingKey
from app.models.reference import AppSetting, Category, Grade
from app.repositories.reference_repo import CategoryRepository, GradeRepository, SettingRepository
from app.schemas.common import Page, PageMeta
from app.schemas.reference import SettingRead

logger = logging.getLogger("scholar.settings")

DEFAULT_SETTINGS: list[dict[str, object]] = [
    {
        "key": SettingKey.CURRENT_YEAR,
        "value": str(env_settings.DEFAULT_CURRENT_YEAR),
        "value_type": "int",
        "description": "Academic year embedded in category titles and Telegram reports.",
    },
    {
        "key": SettingKey.INSTITUTION_NAME,
        "value": "សាលាសិក្សា",
        "value_type": "string",
        "description": "Institution name printed on PDF/Excel exports.",
    },
    {
        "key": SettingKey.DAILY_CUTOFF_TIME,
        "value": "17:00",
        "value_type": "string",
        "description": "Time after which a day is considered closed for reporting.",
    },
    {
        "key": SettingKey.LOCALE,
        "value": "km-KH",
        "value_type": "string",
        "description": "Default locale for generated reports.",
    },
    {"key": SettingKey.TELEGRAM_CHAT_ID, "value": None, "value_type": "string",
     "description": "Default Telegram chat id for daily broadcasts."},
    {"key": SettingKey.TELEGRAM_BOT_TOKEN, "value": None, "value_type": "string",
     "description": "Telegram bot token (stored as a secret).", "is_secret": True},
]


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = SettingRepository(session)
        self.categories = CategoryRepository(session)
        self.grades = GradeRepository(session)

    async def get_current_year(self) -> int:
        value = await self.repo.typed(SettingKey.CURRENT_YEAR)
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return env_settings.DEFAULT_CURRENT_YEAR

    async def set_current_year(self, year: int, updated_by: uuid.UUID | None = None) -> int:
        await self.repo.upsert(
            SettingKey.CURRENT_YEAR,
            year,
            value_type="int",
            description="Academic year embedded in category titles and Telegram reports.",
            updated_by=updated_by,
        )
        clear_cached_titles()
        return year

    async def get(self, key: str, default: str | None = None) -> str | None:
        row = await self.repo.get_setting(key)
        if row is None:
            return default
        return row.value

    async def typed(self, key: str, default=None):  # noqa: ANN001, ANN201
        return await self.repo.typed(key, default)

    async def list_settings(self) -> list[SettingRead]:
        rows = await self.repo.all_settings()
        return [self._to_schema(row) for row in rows]

    async def update_setting(
        self, key: str, value, updated_by: uuid.UUID | None = None  # noqa: ANN001
    ) -> SettingRead:
        if not await self.repo.get_setting(key):
            raise KeyError(f"Unknown setting: {key}")
        value_type = "string"
        if isinstance(value, bool):
            value_type = "bool"
        elif isinstance(value, int):
            value_type = "int"
        row = await self.repo.upsert(key, value, value_type=value_type, updated_by=updated_by)
        clear_cached_titles()
        return self._to_schema(row)

    async def ensure_defaults(self) -> None:
        for spec in DEFAULT_SETTINGS:
            if await self.repo.get_by(key=str(spec["key"])) is None:
                await self.repo.upsert(
                    str(spec["key"]),
                    spec.get("value"),
                    value_type=str(spec.get("value_type", "string")),
                    description=spec.get("description"),
                    is_secret=bool(spec.get("is_secret", False)),
                )

    # ---------------------------------------------------------- references
    async def list_categories(self, active_only: bool = True) -> list[Category]:
        return await self.categories.list_ordered(active_only=active_only)

    async def list_grades(self, active_only: bool = True) -> list[Grade]:
        return await self.grades.list_ordered(active_only=active_only)

    async def ensure_reference_data(self) -> None:
        """Idempotently create the three categories, five grades and settings."""
        from app.models.enums import CATEGORY_ROMAN
        from app.services.reference_defaults import CATEGORY_DEFAULTS

        existing = {c.code: c for c in await self.categories.list_ordered(active_only=False)}
        for spec in CATEGORY_DEFAULTS:
            if spec["code"] in existing:
                continue
            self.categories.add(
                Category(
                    code=spec["code"],
                    position=spec["position"],
                    roman_numeral=CATEGORY_ROMAN.get(spec["code"], spec["roman_numeral"]),
                    title_template=spec["title_template"],
                    is_active=True,
                    description=spec.get("description"),
                )
            )
        grades = {g.code: g for g in await self.grades.list_ordered(active_only=False)}
        for code, position in Grade.default_order():
            if code not in grades:
                self.grades.add(Grade(code=code, position=position, label=f"Grade {code}"))
        await self.repo.session.flush()
        await self.ensure_defaults()

    @staticmethod
    def _to_schema(row: AppSetting) -> SettingRead:
        return SettingRead(
            key=row.key,
            value="********" if row.is_secret and row.value else row.typed_value(),
            value_type=row.value_type,
            description=row.description,
            is_secret=row.is_secret,
            updated_at=row.updated_at.isoformat() if row.updated_at else None,
        )


def clear_cached_titles() -> None:
    """Invalidate the memoised category titles when the year changes."""
    lru_cache.cache_clear()
