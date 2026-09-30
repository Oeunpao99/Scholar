"""Audit trail service."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AuditAction
from app.models.user import AuditLog, User
from app.repositories.audit_repo import AuditRepository
from app.schemas.common import Page, PageMeta

logger = logging.getLogger("scholar.audit")

# Values that must never be written to the audit trail.
_SECRET_KEYS = {"password", "hashed_password", "new_password", "token", "bot_token", "secret_key"}


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AuditRepository(session)

    async def log(
        self,
        *,
        action: AuditAction | str,
        entity_type: str,
        entity_id: str | uuid.UUID | None = None,
        summary: str | None = None,
        changes: dict[str, Any] | None = None,
        user: User | None = None,
        user_id: uuid.UUID | None = None,
        request_meta: dict[str, Any] | None = None,
    ) -> AuditLog:
        meta = request_meta or {}
        entry = AuditLog(
            user_id=user.id if user else user_id,
            user_email=user.email if user else None,
            action=str(action),
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            summary=summary,
            changes=_sanitize(changes) if changes else None,
            ip_address=_normalize_ip(meta.get("ip")),
            user_agent=(meta.get("user_agent") or None) and str(meta.get("user_agent"))[:400],
        )
        self.repo.add(entry)
        await self.repo.session.flush()
        return entry

    async def diff_log(
        self,
        *,
        entity_type: str,
        entity_id: str | uuid.UUID,
        before: dict[str, Any],
        after: dict[str, Any],
        action: AuditAction = AuditAction.UPDATE,
        user: User | None = None,
        request_meta: dict[str, Any] | None = None,
    ) -> AuditLog | None:
        changes = {
            key: {"from": before.get(key), "to": after.get(key)}
            for key in set(before) | set(after)
            if before.get(key) != after.get(key) and key not in _SECRET_KEYS
        }
        if not changes:
            return None
        return await self.log(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=f"Updated {entity_type} fields: {', '.join(sorted(changes))}",
            changes=changes,
            user=user,
            request_meta=request_meta,
        )

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 25,
        user_id: UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start=None,
        end=None,
        q: str | None = None,
    ) -> Page[AuditLog]:
        items, total = await self.repo.paginate_filtered(
            page=page,
            size=size,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            start=start,
            end=end,
            q=q,
        )
        return Page(items=list(items), meta=PageMeta(page=page, size=size, total=total,
                                                     total_pages=(total + size - 1) // size))

    async def history_for(self, entity_type: str, entity_id: str | uuid.UUID) -> list[AuditLog]:
        return await self.repo.recent_for_entity(entity_type, entity_id)


def _sanitize(data: dict[str, Any]) -> dict[str, Any]:
    return {k: ("***" if k in _SECRET_KEYS else v) for k, v in data.items()}


def _normalize_ip(value: Any) -> str | None:
    if not value:
        return None
    import ipaddress

    text = str(value).strip()
    if "," in text:
        text = text.split(",")[0].strip()
    if ":" in text and text.count(":") == 1:
        text = text.split(":")[0]
    if text.startswith("::ffff:"):
        text = text[7:]
    try:
        ipaddress.ip_address(text)
        return text
    except ValueError:
        return None

