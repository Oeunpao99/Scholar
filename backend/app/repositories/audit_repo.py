"""Audit log data access."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.user import AuditLog
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def paginate_filtered(
        self,
        *,
        page: int,
        size: int,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start: date | None = None,
        end: date | None = None,
        q: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog).options(joinedload(AuditLog.user))
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if start:
            conditions.append(AuditLog.created_at >= datetime.combine(start, datetime.min.time()))
        if end:
            conditions.append(AuditLog.created_at <= datetime.combine(end, datetime.max.time()))
        if q:
            like = f"%{q.strip()}%"
            conditions.append(
                AuditLog.summary.ilike(like) | AuditLog.entity_id.ilike(like) | AuditLog.user_email.ilike(like)
            )
        if conditions:
            from sqlalchemy import and_

            stmt = stmt.where(and_(*conditions))
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * size).limit(size)
        return list((await self.session.scalars(stmt)).unique().all()), total

    async def recent(self, limit: int = 10) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(joinedload(AuditLog.user))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique().all())

    async def recent_for_entity(self, entity_type: str, entity_id: str, limit: int = 20) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == str(entity_id))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique().all())

    async def distinct_actions(self) -> Sequence[str]:
        stmt = select(AuditLog.action).distinct().order_by(AuditLog.action)
        return list((await self.session.scalars(stmt)).all())
