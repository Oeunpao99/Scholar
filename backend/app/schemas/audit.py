"""Audit log schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import field_validator

from app.schemas.common import SchemaBase


class AuditLogRead(SchemaBase):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str | None = None
    changes: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime | None = None

    @field_validator("ip_address", mode="before")
    @classmethod
    def _coerce_ip(cls, v: Any) -> str | None:
        if v is not None:
            return str(v)
        return None
