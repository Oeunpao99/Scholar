"""Shared helpers: pagination params, date ranges, Khmer formatting."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class PageParams:
    page: int = 1
    size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def build_page_meta(total: int, params: PageParams) -> dict[str, Any]:
    total_pages = (total + params.size - 1) // params.size if params.size else 0
    return {
        "page": params.page,
        "size": params.size,
        "total": total,
        "total_pages": total_pages,
        "has_next": params.page < total_pages,
        "has_prev": params.page > 1,
    }


def parse_date(value: str | date | datetime | None) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value.strip()[:10])


def month_bounds(target: date) -> tuple[date, date]:
    start = target.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1) - _one_day()
    else:
        end = start.replace(month=start.month + 1, day=1) - _one_day()
    return start, end


def year_bounds(target: date) -> tuple[date, date]:
    return date(target.year, 1, 1), date(target.year, 12, 31)


def _one_day() -> timedelta:
    from datetime import timedelta

    return timedelta(days=1)


def local_today() -> date:
    """Today's date in the configured business timezone."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo(settings.REPORTS_TIMEZONE)).date()
    except Exception:  # pragma: no cover - zoneinfo missing on some images
        return datetime.now(UTC).date()


def format_number(value: int | float) -> str:
    """Two-digit zero padded number, as required by the Telegram report."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "00"
    sign = "-" if number < 0 else ""
    return f"{sign}{abs(number):02d}"


def format_date_dmy(value: date) -> str:
    return f"{value.day:02d}/{value.month:02d}/{value.year}"


def normalize_text(value: str) -> str:
    """NFKC-normalise, collapse whitespace and lowercase for comparisons."""
    if not value:
        return ""
    folded = unicodedata.normalize("NFKC", value)
    return " ".join(folded.split()).lower()


def ensure_utc(value: datetime | None) -> datetime | None:
    """Return a timezone-aware UTC datetime (DB stores naive UTC)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def start_of_day(value: date) -> datetime:
    return datetime.combine(value, time.min)


def end_of_day(value: date) -> datetime:
    return datetime.combine(value, time.max)
