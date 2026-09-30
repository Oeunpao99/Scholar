"""Daily report, grade entry, cumulative and search schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from typing import Any

from pydantic import Field, model_validator

from app.models.enums import GradeLetter
from app.schemas.common import Counters, NonNegativeInt, SchemaBase


class GradeEntryInput(SchemaBase):
    grade: GradeLetter
    total: NonNegativeInt = 0
    female: NonNegativeInt = 0
    pp: NonNegativeInt = 0
    kp: NonNegativeInt = 0

    @model_validator(mode="before")
    @classmethod
    def _normalize_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "today_total" in data and "total" not in data:
                data["total"] = data["today_total"]
            if "today_female" in data and "female" not in data:
                data["female"] = data["today_female"]
            if "today_pp" in data and "pp" not in data:
                data["pp"] = data["today_pp"]
            if "today_kp" in data and "kp" not in data:
                data["kp"] = data["today_kp"]
        return data

    def counters(self) -> Counters:
        return Counters(total=self.total, female=self.female, pp=self.pp, kp=self.kp)


class GradeEntryRead(Counters):
    id: uuid.UUID | None = None
    grade: GradeLetter
    position: int = 4
    is_active: bool = True


class DailyReportCreate(SchemaBase):
    report_date: date | None = None
    category_id: uuid.UUID | str | None = None
    grades: list[GradeEntryInput] = Field(default_factory=list)
    total: NonNegativeInt = 0
    female: NonNegativeInt = 0
    pp: NonNegativeInt = 0
    kp: NonNegativeInt = 0
    note: str | None = Field(default=None, max_length=2000)
    source: str = "manual"
    recompute_totals: bool = Field(
        default=True,
        description="Derive the report totals from the per-grade entries when true.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_incoming(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "date" in data and "report_date" not in data:
                data["report_date"] = data["date"]
            if "category_code" in data and "category_id" not in data:
                data["category_id"] = data["category_code"]
            if "today_total" in data and "total" not in data:
                data["total"] = data["today_total"]
            if "today_female" in data and "female" not in data:
                data["female"] = data["today_female"]
            if "today_pp" in data and "pp" not in data:
                data["pp"] = data["today_pp"]
            if "today_kp" in data and "kp" not in data:
                data["kp"] = data["today_kp"]
        return data

    @model_validator(mode="after")
    def _validate(self) -> DailyReportCreate:
        if self.report_date is None:
            raise ValueError("report_date is required")
        if self.category_id is None:
            raise ValueError("category_id is required")
        self._validate_grades()
        if self.recompute_totals and self.grades:
            summed = sum(g.total for g in self.grades)
            if (self.total, self.female, self.pp, self.kp) == (0, 0, 0, 0):
                self.total = summed
                self.female = sum(g.female for g in self.grades)
                self.pp = sum(g.pp for g in self.grades)
                self.kp = sum(g.kp for g in self.grades)
        self._validate_totals()
        return self

    def _validate_grades(self) -> None:
        seen: set[GradeLetter] = set()
        for entry in self.grades:
            if entry.grade in seen:
                raise ValueError(f"Duplicate grade entry: {entry.grade}")
            seen.add(entry.grade)
            if entry.female > entry.total:
                raise ValueError(f"Grade {entry.grade}: female cannot exceed total")
            if entry.pp + entry.kp > entry.total:
                raise ValueError(f"Grade {entry.grade}: PP + KP cannot exceed total")

    def _validate_totals(self) -> None:
        if self.female > self.total:
            raise ValueError("female cannot exceed total")
        if self.pp + self.kp > self.total:
            raise ValueError("pp + kp cannot exceed total")
        if self.grades:
            if sum(g.total for g in self.grades) != self.total:
                raise ValueError("Sum of grade totals must equal the report total")
            if sum(g.female for g in self.grades) != self.female:
                raise ValueError("Sum of grade females must equal the report female")
            if sum(g.pp for g in self.grades) != self.pp:
                raise ValueError("Sum of grade PP must equal the report PP")
            if sum(g.kp for g in self.grades) != self.kp:
                raise ValueError("Sum of grade KP must equal the report KP")

    def totals_counters(self) -> Counters:
        return Counters(total=self.total, female=self.female, pp=self.pp, kp=self.kp)


class DailyReportUpdate(SchemaBase):
    report_date: date | None = None
    category_id: uuid.UUID | str | None = None
    grades: list[GradeEntryInput] | None = None
    total: NonNegativeInt | None = None
    female: NonNegativeInt | None = None
    pp: NonNegativeInt | None = None
    kp: NonNegativeInt | None = None
    note: str | None = None
    is_locked: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_incoming(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "date" in data and "report_date" not in data:
                data["report_date"] = data["date"]
            if "category_code" in data and "category_id" not in data:
                data["category_id"] = data["category_code"]
            if "today_total" in data and "total" not in data:
                data["total"] = data["today_total"]
            if "today_female" in data and "female" not in data:
                data["female"] = data["today_female"]
            if "today_pp" in data and "pp" not in data:
                data["pp"] = data["today_pp"]
            if "today_kp" in data and "kp" not in data:
                data["kp"] = data["today_kp"]
        return data

    @model_validator(mode="after")
    def _validate(self) -> DailyReportUpdate:
        if self.grades:
            seen: set[GradeLetter] = set()
            for entry in self.grades:
                if entry.grade in seen:
                    raise ValueError(f"Duplicate grade entry: {entry.grade}")
                seen.add(entry.grade)
                if entry.female > entry.total:
                    raise ValueError(f"Grade {entry.grade}: female cannot exceed total")
                if entry.pp + entry.kp > entry.total:
                    raise ValueError(f"Grade {entry.grade}: PP + KP cannot exceed total")
        if self.female is not None and self.total is not None and self.female > self.total:
            raise ValueError("female cannot exceed total")
        if self.pp is not None and self.kp is not None and self.total is not None and self.pp + self.kp > self.total:
            raise ValueError("pp + kp cannot exceed total")
        return self


class DailyReportBulkCreate(SchemaBase):
    reports: list[DailyReportCreate] = Field(min_length=1, max_length=60)


class DailyReportRead(SchemaBase):
    id: uuid.UUID
    report_date: date
    category_id: uuid.UUID
    category_code: str | None = None
    category_title: str | None = None
    roman_numeral: str | None = None
    today: Counters = Field(default_factory=Counters)
    cumulative: Counters = Field(default_factory=Counters)
    today_total: int = 0
    today_female: int = 0
    today_pp: int = 0
    today_kp: int = 0
    grades: list[GradeEntryRead] = Field(default_factory=list)
    note: str | None = None
    source: str = "manual"
    is_locked: bool = False
    created_by: uuid.UUID | None = None
    created_by_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DailyReportDetail(DailyReportRead):
    """Adds the per-grade cumulative split and derived helpers."""

    grade_cumulative: dict[str, Counters] = Field(default_factory=dict)
    male: int = 0
    is_consistent: bool = True
    telegram_preview: str | None = None


class ReportSearchResult(SchemaBase):
    report_date: date
    category_code: str
    category_title: str
    total: int
    female: int
    male: int
    pp: int
    kp: int
    grade_d_total: int = 0


class SearchResponse(SchemaBase):
    query: str
    results: list[ReportSearchResult]
    total: int


class SnapshotRead(SchemaBase):
    report_date: date
    category_id: uuid.UUID
    category_code: str
    cumulative: Counters
    grade_cumulative: dict[str, Counters] = Field(default_factory=dict)
    computed_at: datetime | None = None


class DeleteResult(SchemaBase):
    id: uuid.UUID
    deleted: bool = True
    recomputed_from: date | None = None
