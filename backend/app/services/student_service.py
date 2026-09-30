"""Student list service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.enums import AuditAction
from app.models.student import Student
from app.models.user import User
from app.repositories.student_repo import StudentRepository
from app.schemas.common import Page, PageMeta
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.audit_service import AuditService
from app.services.settings_service import SettingsService


class StudentService:
    def __init__(self, session: AsyncSession, actor: User | None = None) -> None:
        self.session = session
        self.actor = actor
        self.repo = StudentRepository(session)
        self.audit = AuditService(session)
        self.settings = SettingsService(session)

    async def list(
        self,
        *,
        page: int = 1,
        size: int = 50,
        academic_year: int | None = None,
        q: str | None = None,
        gender: str | None = None,
        grade: str | None = None,
        stream: str | None = None,
    ) -> Page[Student]:
        items, total = await self.repo.search(
            academic_year=academic_year,
            q=q,
            gender=gender,
            grade=grade,
            stream=stream,
            limit=size,
            offset=(page - 1) * size,
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

    async def get(self, student_id: UUID) -> Student:
        student = await self.repo.get(student_id)
        if student is None:
            raise NotFoundError("Student not found.")
        return student

    async def create(self, payload: StudentCreate) -> Student:
        data = payload.model_dump()
        if data.get("academic_year") is None:
            data["academic_year"] = await self.settings.get_current_year()
        student = Student(**data, created_by=self.actor.id if self.actor else None)
        self.repo.add(student)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.CREATE,
            entity_type="student",
            entity_id=student.id,
            summary=f"Added student {student.full_name}",
            user=self.actor,
        )
        await self.session.commit()
        return student

    async def update(self, student_id: UUID, payload: StudentUpdate) -> Student:
        student = await self.get(student_id)
        data = payload.model_dump(exclude_unset=True)
        # Required columns can't be cleared.
        for key in ("full_name", "gender", "academic_year"):
            if key in data and data[key] is None:
                data.pop(key)
        before = student.to_dict()
        for key, value in data.items():
            setattr(student, key, value)
        await self.session.flush()
        await self.audit.diff_log(
            entity_type="student",
            entity_id=student.id,
            before={k: before.get(k) for k in data},
            after=data,
            user=self.actor,
        )
        await self.session.commit()
        return student

    async def delete(self, student_id: UUID) -> None:
        student = await self.get(student_id)
        name = student.full_name
        await self.session.delete(student)
        await self.session.flush()
        await self.audit.log(
            action=AuditAction.DELETE,
            entity_type="student",
            entity_id=student_id,
            summary=f"Deleted student {name}",
            user=self.actor,
        )
        await self.session.commit()
