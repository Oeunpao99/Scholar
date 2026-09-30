"""students list

Adds the named student list (name, gender, grade, score rank, high school,
stream, requested university, major, phone, notes) per academic year.

Revision ID: 0003_students
Revises: 0002_reference_data
Create Date: 2026-09-30 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_students"
down_revision: str | None = "0002_reference_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "students",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("academic_year", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=1), nullable=False),
        sa.Column("grade", sa.String(length=1), nullable=True),
        sa.Column("score_rank", sa.Integer(), nullable=True),
        sa.Column("high_school", sa.String(length=255), nullable=True),
        sa.Column("stream", sa.String(length=32), nullable=True),
        sa.Column("university", sa.String(length=255), nullable=True),
        sa.Column("major", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint("gender IN ('M', 'F')", name="ck_students_gender_valid"),
        sa.CheckConstraint(
            "grade IS NULL OR grade IN ('A', 'B', 'C', 'D', 'E')", name="ck_students_grade_valid"
        ),
        sa.CheckConstraint(
            "stream IS NULL OR stream IN ('science', 'social_science')",
            name="ck_students_stream_valid",
        ),
        sa.CheckConstraint("score_rank IS NULL OR score_rank > 0", name="ck_students_score_rank_positive"),
    )
    op.create_index("ix_students_year_created", "students", ["academic_year", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_students_year_created", table_name="students")
    op.drop_table("students")
