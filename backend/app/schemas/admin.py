"""Administration schemas."""

from __future__ import annotations

from typing import Any

from app.schemas.common import SchemaBase


class BackupInfoRead(SchemaBase):
    filename: str
    size_bytes: int
    size_display: str
    created_at: str
    format: str


class RestoreResult(SchemaBase):
    restored: bool = True
    source: str
    format: str
    clean: bool = True


class HealthRead(SchemaBase):
    status: str
    environment: str
    server_time: str
    timezone: str
    backup_dir: str


class ExportResult(SchemaBase):
    """Metadata returned alongside a generated export (used by tests/tooling)."""

    filename: str
    media_type: str
    rows: int
    metadata: dict[str, Any] = {}
