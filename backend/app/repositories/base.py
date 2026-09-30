"""Generic async CRUD repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Thin data-access wrapper providing CRUD and simple predicates."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------- reading
    async def get(self, entity_id: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def get_by(self, **filters: Any) -> ModelT | None:
        stmt = select(self.model).filter_by(**filters).limit(1)
        return await self._one(stmt)

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ModelT]:
        stmt = self._base_query(filters, order_by)
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**(filters or {}))
        return int((await self.session.execute(stmt)).scalar_one())

    async def exists(self, **filters: Any) -> bool:
        return (await self.count(filters)) > 0

    async def first(self, stmt: Select) -> ModelT | None:
        return await self._one(stmt)

    async def scalars(self, stmt: Select) -> Sequence[ModelT]:
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    # ------------------------------------------------------------- writing
    def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        return entity

    def add_all(self, entities: Sequence[ModelT]) -> None:
        self.session.add_all(list(entities))

    async def delete_by_id(self, entity_id: uuid.UUID) -> bool:
        entity = await self.get(entity_id)
        if entity is None:
            return False
        await self.session.delete(entity)
        return True

    async def delete_where(self, **filters: Any) -> int:
        stmt = delete(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def update_where(self, values: dict[str, Any], **filters: Any) -> int:
        stmt = update(self.model).filter_by(**filters).values(**values)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    # -------------------------------------------------------------- helpers
    def _base_query(
        self, filters: dict[str, Any] | None = None, order_by: str | None = None
    ) -> Select:
        stmt = select(self.model)
        if filters:
            stmt = stmt.filter_by(**filters)
        if order_by:
            stmt = stmt.order_by(_resolve_order(self.model, order_by))
        return stmt

    async def _one(self, stmt: Select) -> ModelT | None:
        result = await self.session.execute(stmt.limit(1))
        return result.scalars().unique().first()

    async def paginate(
        self, stmt: Select, page: int, size: int
    ) -> tuple[list[ModelT], int]:
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        result = await self.session.execute(stmt.offset((page - 1) * size).limit(size))
        return list(result.scalars().unique().all()), total


def _resolve_order(model: type[Base], order_by: str) -> Any:
    column = getattr(model, order_by, None)
    if column is None:
        raise AttributeError(f"{model.__name__} has no column {order_by!r}")
    return column.asc() if not order_by.startswith("-") else column.desc()
