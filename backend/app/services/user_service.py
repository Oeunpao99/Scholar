"""User administration service."""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.security import hash_password
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import UserCreate, UserRead, UserUpdate
from app.schemas.common import Page, PageMeta
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

logger = logging.getLogger("scholar.users")


class UserService:
    def __init__(self, session: AsyncSession, actor: User | None = None) -> None:
        self.session = session
        self.actor = actor
        self.repo = UserRepository(session)
        self.audit = AuditService(session)

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 20,
        q: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> Page[User]:
        items, total = await self.repo.search(
            q=q, role=role, is_active=is_active, limit=size, offset=(page - 1) * size
        )
        return Page(
            items=items,
            meta=PageMeta(
                page=page,
                size=size,
                total=total,
                total_pages=(total + size - 1) // size,
                has_next=page * size < total,
                has_prev=page > 1,
            ),
        )

    async def get(self, user_id: UUID) -> User:
        user = await self.repo.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def create(self, payload: UserCreate) -> User:
        await self._assert_unique(payload.email, payload.username)
        user = User(
            email=payload.email.lower(),
            username=payload.username,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            phone=payload.phone,
            telegram_chat_id=payload.telegram_chat_id,
            note=payload.note,
            is_active=payload.is_active,
            is_superuser=payload.role == UserRole.SUPERADMIN,
        )
        self.repo.add(user)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.CREATE,
            entity_type="user",
            entity_id=user.id,
            summary=f"Created user {user.username} ({user.role})",
            user=self.actor,
        )
        await self.session.commit()
        return user

    async def update(self, user_id: UUID, payload: UserUpdate) -> User:
        user = await self.get(user_id)
        data = payload.model_dump(exclude_unset=True)
        if "email" in data and data["email"]:
            await self._assert_unique(data["email"], None, exclude_id=user_id)
            data["email"] = data["email"].lower()
        if "role" in data and data["role"]:
            if data["role"] == UserRole.SUPERADMIN:
                data["is_superuser"] = True
            elif user.is_superuser and user.id == (self.actor.id if self.actor else None):
                raise ValidationError("You cannot remove your own superadmin role.")
        before = user.to_dict()
        for key, value in data.items():
            setattr(user, key, value)
        await self.session.flush()
        await self.audit.diff_log(
            entity_type="user",
            entity_id=user.id,
            before={k: before.get(k) for k in data},
            after=data,
            user=self.actor,
        )
        await self.session.commit()
        return user

    async def delete(self, user_id: UUID) -> None:
        user = await self.get(user_id)
        if self.actor and user.id == self.actor.id:
            raise ValidationError("You cannot delete your own account.")
        if user.is_superuser and await self.repo.count_by_role().get(UserRole.SUPERADMIN, 0) <= 1:
            raise ValidationError("The last superadmin account cannot be deleted.")
        await self.session.delete(user)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            entity_type="user",
            entity_id=user_id,
            summary=f"Deleted user {user.username}",
            user=self.actor,
        )
        await self.session.commit()

    async def set_active(self, user_id: UUID, is_active: bool) -> User:
        user = await self.get(user_id)
        if not is_active and self.actor and user.id == self.actor.id:
            raise ValidationError("You cannot deactivate your own account.")
        user.is_active = is_active
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.UPDATE,
            entity_type="user",
            entity_id=user.id,
            summary=f"{'Activated' if is_active else 'Deactivated'} {user.username}",
            changes={"is_active": is_active},
            user=self.actor,
        )
        await self.session.commit()
        return user

    async def reset_password(self, user_id: UUID, new_password: str) -> None:
        user = await self.get(user_id)
        if self.actor is None:
            raise ValidationError("An authenticated actor is required.")
        await AuthService(self.session).reset_password(user, new_password, self.actor)
        await self.session.commit()

    async def stats(self) -> dict[str, int]:
        counts = await self.repo.count_by_role()
        total = await self.repo.count()
        active = await self.repo.count({"is_active": True})
        return {"total": total, "active": active, "inactive": total - active, **counts}

    async def read(self, user: User) -> UserRead:
        return UserRead.from_entity(user)

    async def _assert_unique(
        self, email: str, username: str | None, exclude_id: UUID | None = None
    ) -> None:
        existing = await self.repo.get_by_email(email)
        if existing and existing.id != exclude_id:
            raise ConflictError("A user with that email already exists.")
        if username:
            found = await self.repo.get_by_username(username)
            if found and found.id != exclude_id:
                raise ConflictError("That username is already taken.")
