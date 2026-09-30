"""User and refresh-token data access."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.refresh_tokens: RefreshTokenRepository = RefreshTokenRepository(session)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(func.lower(User.username) == username.strip().lower())
        return await self.first(stmt)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return await self.first(stmt)

    async def get_optional_by_identifier(self, identifier: str) -> User | None:
        return (await self.get_by_username(identifier)) or (await self.get_by_email(identifier))

    async def get_with_tokens(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).options(selectinload(User.refresh_tokens)).where(User.id == user_id)
        return await self.first(stmt)

    async def search(
        self, *, q: str | None, role: str | None, is_active: bool | None, limit: int, offset: int
    ) -> tuple[list[User], int]:
        stmt = select(User)
        if q:
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(User.username).like(like)
                | func.lower(User.email).like(like)
                | func.lower(func.coalesce(User.full_name, "")).like(like)
            )
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
        return list((await self.session.scalars(stmt)).all()), total

    async def count_by_role(self) -> dict[str, int]:
        stmt = select(User.role, func.count()).group_by(User.role)
        return {role: int(count) for role, count in (await self.session.execute(stmt)).all()}


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_valid(self, token: str, now: datetime) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.token == token,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return await self.first(stmt)

    async def revoke_for_user(self, user_id: uuid.UUID, now: datetime) -> int:
        return await self.update_where({"revoked_at": now}, user_id=user_id, revoked_at=None)

    async def purge_expired(self, now: datetime) -> int:
        stmt = select(RefreshToken.id).where(RefreshToken.expires_at < now)
        ids = list((await self.session.scalars(stmt)).all())
        if not ids:
            return 0
        for token_id in ids:
            await self.session.delete(await self.get(token_id))  # type: ignore[arg-type]
        return len(ids)
