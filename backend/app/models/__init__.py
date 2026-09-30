"""Model package - importing this module registers every table on the metadata."""

from app.db.base import Base
from app.models.enums import (
    CATEGORY_ORDER,
    CATEGORY_ROMAN,
    GRADE_ORDER,
    AuditAction,
    CategoryCode,
    ExportFormat,
    GradeLetter,
    ReportScope,
    UserRole,
)
from app.models.reference import AppSetting, Category, Grade
from app.models.report import DailyGradeEntry, DailyReport, DailyTotalsSnapshot
from app.models.student import Student, StudentPhoto
from app.models.user import AuditLog, RefreshToken, User

__all__ = [
    "Base",
    "User",
    "RefreshToken",
    "AuditLog",
    "AppSetting",
    "Category",
    "Grade",
    "DailyReport",
    "DailyGradeEntry",
    "DailyTotalsSnapshot",
    "Student",
    "StudentPhoto",
    "GradeLetter",
    "CategoryCode",
    "UserRole",
    "AuditAction",
    "ExportFormat",
    "ReportScope",
    "GRADE_ORDER",
    "CATEGORY_ORDER",
    "CATEGORY_ROMAN",
]
