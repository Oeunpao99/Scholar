"""Domain enumerations shared by models, schemas and services."""

from __future__ import annotations

from enum import StrEnum


class GradeLetter(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


GRADE_ORDER: tuple[str, ...] = ("A", "B", "C", "D", "E")


class CategoryCode(StrEnum):
    """Stable machine codes; the display title embeds the current year."""

    CURRENT_YEAR = "current_year"
    BEFORE_CURRENT_YEAR = "before_current_year"
    OTHER_PROVINCE = "other_province"


class Metric(StrEnum):
    """The four counts tracked for every grade, category and cumulative row."""

    TOTAL = "total"
    FEMALE = "female"
    PP = "pp"
    KP = "kp"


METRIC_ORDER: tuple[str, ...] = (
    Metric.TOTAL,
    Metric.FEMALE,
    Metric.PP,
    Metric.KP,
)


CATEGORY_ORDER: tuple[str, ...] = (
    CategoryCode.CURRENT_YEAR,
    CategoryCode.BEFORE_CURRENT_YEAR,
    CategoryCode.OTHER_PROVINCE,
)

CATEGORY_ROMAN: dict[str, str] = {
    CategoryCode.CURRENT_YEAR: "I.",
    CategoryCode.BEFORE_CURRENT_YEAR: "II.",
    CategoryCode.OTHER_PROVINCE: "III.",
}


class UserRole(StrEnum):
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    VIEWER = "viewer"


class ReportScope(StrEnum):
    DAILY = "daily"
    MONTHLY = "monthly"
    RANGE = "range"


class ExportFormat(StrEnum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"
    TELEGRAM = "telegram"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    BACKUP = "backup"
    RESTORE = "restore"
    AI_PARSE = "ai_parse"
    SETTINGS_CHANGE = "settings_change"
    SEND = "send"


class SettingKey(StrEnum):
    CURRENT_YEAR = "current_year"
    INSTITUTION_NAME = "institution_name"
    TELEGRAM_CHAT_ID = "telegram_chat_id"
    TELEGRAM_BOT_TOKEN = "telegram_bot_token"
    DAILY_CUTOFF_TIME = "daily_cutoff_time"
    LOCALE = "locale"
