"""student photos

One photo per student (cropped from the scanned form or uploaded by hand),
in its own table so student lists never load image bytes.

Revision ID: 0004_student_photos
Revises: 0003_students
Create Date: 2026-09-30 01:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_student_photos"
down_revision: str | None = "0003_students"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_photos",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("student_photos")
