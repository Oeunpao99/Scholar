"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings. All values are overridable via environment variables."""

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", BACKEND_ROOT.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------ app
    PROJECT_NAME: str = "Scholar - Daily Student Enrollment Management System"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]
    )

    # ------------------------------------------------------------- database
    POSTGRES_USER: str = "scholar"
    POSTGRES_PASSWORD: str = "scholar"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "scholar"
    DATABASE_URL: str | None = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ----------------------------------------------------------------- auth
    SECRET_KEY: str = "change-me-in-production-please-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    FIRST_SUPERUSER_EMAIL: str = "admin@scholar.local"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"

    # ---------------------------------------------------------------- redis
    REDIS_URL: str | None = None

    # ------------------------------------------------------------- business
    DEFAULT_CURRENT_YEAR: int = 2026
    TIMEZONE: str = "Asia/Phnom_Penh"
    REPORTS_TIMEZONE: str = "Asia/Phnom_Penh"

    # --------------------------------------------------------------- storage
    STORAGE_DIR: Path = BACKEND_ROOT.parent / "storage"
    BACKUP_DIR: Path = BACKEND_ROOT.parent / "storage" / "backups"
    MAX_UPLOAD_SIZE_MB: int = 12

    # ------------------------------------------------------------------- ai
    AI_PROVIDER: str = "builtin"
    AI_LLM_BASE_URL: str | None = None
    AI_LLM_API_KEY: str | None = None
    AI_LLM_MODEL: str = "gpt-4o-mini"
    AI_LLM_TIMEOUT_SECONDS: float = 45.0
    OCR_ENABLED: bool = True
    OCR_LANGUAGES: str = "khm+eng"
    TESSERACT_CMD: str | None = None

    # ------------------------------------------------------------ rate limit
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "600/minute"
    RATE_LIMIT_LOGIN: str = "10/minute"
    RATE_LIMIT_AI: str = "30/minute"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def async_database_url(self) -> str:
        """Async SQLAlchemy DSN."""
        if self.DATABASE_URL:
            url = self.DATABASE_URL
        else:
            url = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        # Allow an asyncpg URL in config but force the async driver.
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Synchronous DSN - used by Alembic and the backup service."""
        url = self.async_database_url
        for async_driver, sync_driver in (
            ("postgresql+asyncpg", "postgresql+psycopg"),
            ("sqlite+aiosqlite", "sqlite"),
        ):
            if url.startswith(async_driver):
                return url.replace(async_driver, sync_driver, 1)
        return url

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (safe to use as a FastAPI dependency)."""
    settings = Settings()
    settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
