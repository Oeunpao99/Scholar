"""AI extraction schemas (unstructured Khmer/English text -> structured data)."""

from __future__ import annotations

from datetime import date as Date

from pydantic import Field, model_validator

from app.models.enums import GradeLetter
from app.schemas.common import Counters, NonNegativeInt, SchemaBase


class ExtractedGrade(SchemaBase):
    grade: GradeLetter
    total: NonNegativeInt = 0
    female: NonNegativeInt = 0
    pp: NonNegativeInt = 0
    kp: NonNegativeInt = 0


class ExtractedCategory(SchemaBase):
    category: str = Field(description="current_year | before_current_year | other_province")
    title: str | None = None
    grades: list[ExtractedGrade] = Field(default_factory=list)
    total: NonNegativeInt = 0
    female: NonNegativeInt = 0
    male: NonNegativeInt = 0
    pp: NonNegativeInt = 0
    kp: NonNegativeInt = 0


class ExtractedReport(SchemaBase):
    date: Date | None = None
    current_year: int | None = None
    categories: list[ExtractedCategory] = Field(default_factory=list)
    source_language: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)

    def flat_grades(self) -> list[ExtractedGrade]:
        return [g for c in self.categories for g in c.grades]

    def total_counters(self) -> Counters:
        total = sum(c.total for c in self.categories)
        female = sum(c.female for c in self.categories)
        pp = sum(c.pp for c in self.categories)
        kp = sum(c.kp for c in self.categories)
        return Counters(total=total, female=female, pp=pp, kp=kp)


class AIParseRequest(SchemaBase):
    text: str = Field(default="", max_length=20000, description="Raw Khmer/English text or OCR output.")
    default_date: Date | None = Field(default=None, description="Fallback when no date is detected.")
    current_year: int | None = None
    provider: str | None = Field(default=None, description="builtin | llm | ocr | llm+ocr")
    images: list[str] = Field(
        default_factory=list, description="Base64 encoded images for OCR extraction."
    )

    @model_validator(mode="after")
    def _require_input(self) -> "AIParseRequest":
        # Text is optional when an image is attached (image-only OCR scans).
        if not self.text.strip() and not self.images:
            raise ValueError("Provide text or at least one image.")
        return self

    @property
    def effective_provider(self) -> str:
        return (self.provider or "builtin").lower()


class AIParseResponse(SchemaBase):
    provider: str
    extracted: ExtractedReport
    preview_text: str | None = None
    ocr_text: str | None = None
    raw_response: str | None = None


class ApplyExtraction(SchemaBase):
    """Persist an extraction result as one or more daily reports."""

    report_date: Date
    category_id: str | None = None
    categories: list[ExtractedCategory] = Field(default_factory=list)
    dry_run: bool = True
