"""Student list schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, field_serializer, field_validator

from app.schemas.common import SchemaBase

Gender = Literal["M", "F"]
GradeCode = Literal["A", "B", "C", "D", "E"]
Stream = Literal["science", "social_science"]

ShortText = Annotated[str, StringConstraints(max_length=255)]
Phone = Annotated[str, StringConstraints(max_length=32)]

_OPTIONAL_TEXT = ("high_school", "university", "major", "phone", "note")


class _StudentFields(SchemaBase):
    @field_validator(*_OPTIONAL_TEXT, "grade", "stream", mode="before", check_fields=False)
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        # Empty form inputs arrive as "" - store them as NULL.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("grade", mode="before", check_fields=False)
    @classmethod
    def _upper_grade(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value


class StudentCreate(_StudentFields):
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
    gender: Gender
    grade: GradeCode | None = None
    score_rank: int | None = Field(default=None, gt=0, le=10_000_000)
    high_school: ShortText | None = None
    stream: Stream | None = None
    university: ShortText | None = None
    major: ShortText | None = None
    phone: Phone | None = None
    note: Annotated[str, StringConstraints(max_length=2000)] | None = None
    academic_year: int | None = Field(
        default=None, ge=2000, le=2100, description="Defaults to the configured current year."
    )


class StudentUpdate(_StudentFields):
    full_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] | None = None
    gender: Gender | None = None
    grade: GradeCode | None = None
    score_rank: int | None = Field(default=None, gt=0, le=10_000_000)
    high_school: ShortText | None = None
    stream: Stream | None = None
    university: ShortText | None = None
    major: ShortText | None = None
    phone: Phone | None = None
    note: Annotated[str, StringConstraints(max_length=2000)] | None = None
    academic_year: int | None = Field(default=None, ge=2000, le=2100)


class StudentRead(SchemaBase):
    id: str
    academic_year: int
    full_name: str
    gender: str
    grade: str | None = None
    score_rank: int | None = None
    high_school: str | None = None
    stream: str | None = None
    university: str | None = None
    major: str | None = None
    phone: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("id", mode="before")
    @classmethod
    def _id_str(cls, value: object) -> object:
        return str(value) if value is not None else value

    @field_serializer("created_at", "updated_at")
    def _ser(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
