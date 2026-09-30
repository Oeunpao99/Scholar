"""Individual student records (the named list behind the daily counts)."""

from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, deferred, mapped_column

from app.db.base import Base, TimestampMixin, utcnow

GENDERS = ("M", "F")
STREAMS = ("science", "social_science")


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("gender IN ('M', 'F')", name="ck_students_gender_valid"),
        CheckConstraint(
            "grade IS NULL OR grade IN ('A', 'B', 'C', 'D', 'E')", name="ck_students_grade_valid"
        ),
        CheckConstraint(
            "stream IS NULL OR stream IN ('science', 'social_science')",
            name="ck_students_stream_valid",
        ),
        CheckConstraint("score_rank IS NULL OR score_rank > 0", name="ck_students_score_rank_positive"),
        Index("ix_students_year_created", "academic_year", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)  # គោត្តនាម-នាម
    gender: Mapped[str] = mapped_column(String(1), nullable=False)  # ភេទ: M / F
    grade: Mapped[str | None] = mapped_column(String(1))  # និ. (A-E)
    score_rank: Mapped[int | None] = mapped_column(Integer)  # លំដាប់ពិន្ទុ
    high_school: Mapped[str | None] = mapped_column(String(255))  # វិទ្យាល័យ
    stream: Mapped[str | None] = mapped_column(String(32))  # ថ្នាក់: science / social_science
    university: Mapped[str | None] = mapped_column(String(255))  # ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន
    major: Mapped[str | None] = mapped_column(String(255))  # ជំនាញ/មុខវិជ្ជា
    phone: Mapped[str | None] = mapped_column(String(32))  # លេខទូរស័ព្ទ
    note: Mapped[str | None] = mapped_column(Text)  # ផ្សេងៗ
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class StudentPhoto(Base):
    """One photo per student, kept apart so listing students never loads image bytes."""

    __tablename__ = "student_photos"

    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), primary_key=True
    )
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default="image/jpeg")
    data: Mapped[bytes] = deferred(mapped_column(LargeBinary, nullable=False))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow,
        server_default=func.now(), nullable=False,
    )
