"""Category, grade and settings data access."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SettingKey
from app.models.reference import AppSetting, Category, Grade
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    model = Category

    async def list_ordered(self, *, active_only: bool = True) -> list[Category]:
        stmt = select(Category)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        stmt = stmt.order_by(Category.position.asc())
        return list((await self.session.scalars(stmt)).all())

    async def get_by_code(self, code: str) -> Category | None:
        return await self.get_by(code=code)

    async def resolve(self, value: str | uuid.UUID) -> Category | None:
        """Resolve a category from an id, code or display title."""
        try:
            if isinstance(value, uuid.UUID) or len(str(value)) == 36:
                found = await self.get(uuid.UUID(str(value)))
                if found:
                    return found
        except (ValueError, AttributeError):
            pass
        found = await self.get_by_code(str(value))
        if found:
            return found
        return None


class GradeRepository(BaseRepository[Grade]):
    model = Grade

    async def list_ordered(self, *, active_only: bool = True) -> list[Grade]:
        stmt = select(Grade)
        if active_only:
            stmt = stmt.where(Grade.is_active.is_(True))
        stmt = stmt.order_by(Grade.position.asc())
        return list((await self.session.scalars(stmt)).all())

    async def positions(self) -> dict[str, int]:
        rows = (await self.session.execute(select(Grade.code, Grade.position))).all()
        return {code: int(position) for code, position in rows}


class SettingRepository(BaseRepository[AppSetting]):
    model = AppSetting

    async def get_setting(self, key: SettingKey | str) -> AppSetting | None:
        return await self.get_by(key=str(key))

    async def typed(self, key: SettingKey | str, default: object = None) -> object:
        row = await self.get_setting(key)
        if row is None:
            return default
        return row.typed_value()

    async def all_settings(self) -> list[AppSetting]:
        return list((await self.session.scalars(select(AppSetting).order_by(AppSetting.key))).all())

    async def upsert(
        self,
        key: str,
        value: object,
        *,
        value_type: str = "string",
        description: str | None = None,
        is_secret: bool = False,
        updated_by: uuid.UUID | None = None,
    ) -> AppSetting:
        row = await self.get_by(key=key)
        serialized = None if value is None else str(value)
        if row is None:
            row = AppSetting(
                key=key,
                value=serialized,
                value_type=value_type,
                description=description,
                is_secret=is_secret,
                updated_by=updated_by,
            )
            self.session.add(row)
        else:
            row.value = serialized
            row.value_type = value_type
            row.is_secret = is_secret
            if description is not None:
                row.description = description
            row.updated_by = updated_by
        await self.session.flush()
        return row
