"""Reference data: settings, categories and grades."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import CategoryCode, GradeLetter


class AppSetting(Base, TimestampMixin):
    """Key/value system settings (current year, bot token, ...)."""

    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("key", name="uq_settings_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[str | None] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(16), nullable=False, default="string", server_default="string")
    description: Mapped[str | None] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    updated_by: Mapped[uuid.UUID | None] = mapped_column()

    def typed_value(self) -> Any:
        raw = self.value
        if raw is None:
            return None
        if self.value_type == "int":
            return int(raw)
        if self.value_type == "bool":
            return raw.lower() in {"1", "true", "yes", "on"}
        if self.value_type == "json":
            import json

            try:
                return json.loads(raw)
            except (TypeError, ValueError):
                return None
        return raw


class Category(Base, TimestampMixin):
    """One of the three applicant categories. Exactly three rows are seeded."""

    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("code", name="uq_categories_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    code: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CategoryCode.CURRENT_YEAR, server_default="current_year"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    roman_numeral: Mapped[str] = mapped_column(
        String(8), nullable=False, default="I.", server_default="I."
    )
    title_template: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="បានទទួលពាក្យបាក់ឌុប{year}",
        server_default="បានទទួលពាក្យបាក់ឌុប{year}",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    def render_title(self, year: int) -> str:
        return self.title_template.format(year=year)


class Grade(Base, TimestampMixin):
    """A/B/C/D/E. ``position`` defines ordering in every report."""

    __tablename__ = "grades"
    __table_args__ = (UniqueConstraint("code", name="uq_grades_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    code: Mapped[str] = mapped_column(
        String(8), nullable=False, default=GradeLetter.D, server_default="D"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    label: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    description: Mapped[str | None] = mapped_column(Text)

    @staticmethod
    def default_order() -> list[tuple[str, int]]:
        return [(g, i + 1) for i, g in enumerate(("A", "B", "C", "D", "E"))]
