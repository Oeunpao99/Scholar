"""Student list data access."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models.student import Student
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    model = Student

    async def search(
        self,
        *,
        academic_year: int | None,
        q: str | None,
        gender: str | None,
        grade: str | None,
        stream: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Student], int]:
        stmt = select(Student)
        if academic_year is not None:
            stmt = stmt.where(Student.academic_year == academic_year)
        if q:
            like = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                func.lower(Student.full_name).like(like)
                | func.lower(func.coalesce(Student.phone, "")).like(like)
                | func.lower(func.coalesce(Student.high_school, "")).like(like)
                | func.lower(func.coalesce(Student.university, "")).like(like)
                | func.lower(func.coalesce(Student.major, "")).like(like)
            )
        if gender:
            stmt = stmt.where(Student.gender == gender)
        if grade:
            stmt = stmt.where(Student.grade == grade)
        if stream:
            stmt = stmt.where(Student.stream == stream)
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        # Entry order, so the row number (ល.រ) stays stable as students are added.
        stmt = stmt.order_by(Student.created_at.asc(), Student.id.asc()).offset(offset).limit(limit)
        return list((await self.session.scalars(stmt)).all()), total
