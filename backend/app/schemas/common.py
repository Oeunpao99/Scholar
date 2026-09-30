"""Shared schema primitives."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_serializer

T = TypeVar("T")

NonNegativeInt = Annotated[int, Field(ge=0, le=10_000_000)]

Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50, pattern=r"^[\w.\-]+$")
]
Password = Annotated[
    str, StringConstraints(min_length=8, max_length=128)
]


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class MessageResponse(SchemaBase):
    message: str
    success: bool = True


class PageMeta(SchemaBase):
    page: int = 1
    size: int = 20
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False


class Page(SchemaBase, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)


class DateRange(SchemaBase):
    start_date: date
    end_date: date

    def validated(self) -> tuple[date, date]:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self.start_date, self.end_date


class Counters(SchemaBase):
    """The four tracked metrics shared by gains, cumulative and AI payloads."""

    total: NonNegativeInt = 0
    female: NonNegativeInt = 0
    pp: NonNegativeInt = 0
    kp: NonNegativeInt = 0

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.total, self.female, self.pp, self.kp

    def __add__(self, other: Counters) -> Counters:
        return Counters(
            total=self.total + other.total,
            female=self.female + other.female,
            pp=self.pp + other.pp,
            kp=self.kp + other.kp,
        )

    def is_zero(self) -> bool:
        return self.total == 0 and self.female == 0 and self.pp == 0 and self.kp == 0


class TimestampedOut(SchemaBase):
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def _ser(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
