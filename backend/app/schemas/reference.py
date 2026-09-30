"""Reference data schemas: settings, categories, grades."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import Field, field_validator

from app.models.enums import CategoryCode
from app.schemas.common import SchemaBase


class CategoryBase(SchemaBase):
    code: CategoryCode
    position: int = Field(ge=1, le=3)
    roman_numeral: str = Field(default="I.", max_length=8)
    title_template: str = Field(min_length=3, max_length=255)
    is_active: bool = True
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(SchemaBase):
    position: int | None = Field(default=None, ge=1, le=3)
    roman_numeral: str | None = None
    title_template: str | None = None
    is_active: bool | None = None
    description: str | None = None


class CategoryRead(CategoryBase):
    id: uuid.UUID
    title: str

    @classmethod
    def from_entity(cls, category: object, year: int) -> CategoryRead:
        return cls(
            id=category.id,
            code=category.code,
            position=category.position,
            roman_numeral=category.roman_numeral,
            title_template=category.title_template,
            is_active=category.is_active,
            description=category.description,
            title=category.title_template.format(year=year),
        )


class GradeBase(SchemaBase):
    code: str = Field(min_length=1, max_length=8)
    position: int = Field(ge=1, le=5)
    label: str | None = None
    is_active: bool = True
    description: str | None = None

    @field_validator("code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper()


class GradeCreate(GradeBase):
    pass


class GradeUpdate(SchemaBase):
    position: int | None = Field(default=None, ge=1, le=5)
    label: str | None = None
    is_active: bool | None = None
    description: str | None = None


class GradeRead(GradeBase):
    id: uuid.UUID


class SettingRead(SchemaBase):
    key: str
    value: Any = None
    value_type: str
    description: str | None = None
    is_secret: bool = False
    updated_at: str | None = None


class SettingUpdate(SchemaBase):
    value: Any = None
    description: str | None = None


class YearUpdate(SchemaBase):
    current_year: int = Field(ge=2000, le=2100)


class CategoryTitleUpdate(SchemaBase):
    title_template: str = Field(min_length=3, max_length=255)
