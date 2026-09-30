"""initial schema

Creates the full normalised schema:
users, refresh_tokens, audit_logs, settings, categories, grades,
daily_reports, daily_grade_entries, daily_totals_snapshot.

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01 00:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB(astext_type=sa.Text())
INET = postgresql.INET()


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"), nullable=False
    )


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # ------------------------------------------------------------- users
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), server_default="staff", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("is_superuser", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("telegram_chat_id", sa.String(length=64), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_role_is_active", "users", ["role", "is_active"])

    # ------------------------------------------------------ refresh_tokens
    op.create_table(
        "refresh_tokens",
        _uuid_pk(),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"])
    op.create_index("ix_refresh_tokens_user_expires", "refresh_tokens", ["user_id", "expires_at"])

    # --------------------------------------------------------- audit_logs
    op.create_table(
        "audit_logs",
        _uuid_pk(),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=32), server_default="update", nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("user_agent", sa.String(length=400), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_created_at_action", "audit_logs", ["created_at", "action"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    # ------------------------------------------------------------ settings
    op.create_table(
        "settings",
        _uuid_pk(),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=16), server_default="string", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_secret", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("updated_by", UUID, nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("key", name="uq_settings_key"),
    )
    op.create_index("ix_settings_key", "settings", ["key"])

    # ---------------------------------------------------------- categories
    op.create_table(
        "categories",
        _uuid_pk(),
        sa.Column("code", sa.String(length=32), server_default="current_year", nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("roman_numeral", sa.String(length=8), server_default="I.", nullable=False),
        sa.Column(
            "title_template",
            sa.String(length=255),
            server_default="បានទទួលពាក្យបាក់ឌុប{year}",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("meta", JSONB, nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_categories_code"),
    )

    # -------------------------------------------------------------- grades
    op.create_table(
        "grades",
        _uuid_pk(),
        sa.Column("code", sa.String(length=8), server_default="D", nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("label", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_grades_code"),
    )

    # -------------------------------------------------------- daily_reports
    op.create_table(
        "daily_reports",
        _uuid_pk(),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("category_id", UUID, nullable=False),
        sa.Column("today_total", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_female", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_pp", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_kp", sa.Integer, server_default="0", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("is_locked", sa.Boolean, server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column("updated_by", UUID, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("report_date", "category_id", name="uq_daily_reports_date_category"),
        sa.CheckConstraint("today_total >= 0", name="ck_daily_reports_today_total_non_negative"),
        sa.CheckConstraint("today_female >= 0", name="ck_daily_reports_today_female_non_negative"),
        sa.CheckConstraint("today_pp >= 0", name="ck_daily_reports_today_pp_non_negative"),
        sa.CheckConstraint("today_kp >= 0", name="ck_daily_reports_today_kp_non_negative"),
        sa.CheckConstraint("today_female <= today_total", name="ck_daily_reports_female_lte_total"),
    )
    op.create_index("ix_daily_reports_report_date", "daily_reports", ["report_date"])
    op.create_index("ix_daily_reports_category_id", "daily_reports", ["category_id"])
    op.create_index("ix_daily_reports_created_by", "daily_reports", ["created_by"])

    # -------------------------------------------------- daily_grade_entries
    op.create_table(
        "daily_grade_entries",
        _uuid_pk(),
        sa.Column("report_id", UUID, nullable=False),
        sa.Column("grade", sa.String(length=8), server_default="D", nullable=False),
        sa.Column("position", sa.Integer, server_default="4", nullable=False),
        sa.Column("today_total", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_female", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_pp", sa.Integer, server_default="0", nullable=False),
        sa.Column("today_kp", sa.Integer, server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["daily_reports.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("report_id", "grade", name="uq_daily_grade_entries_report_grade"),
        sa.CheckConstraint("grade in ('A','B','C','D','E')", name="ck_daily_grade_entries_grade_letter"),
        sa.CheckConstraint("today_total >= 0", name="ck_daily_grade_entries_total_non_negative"),
        sa.CheckConstraint("today_female >= 0", name="ck_daily_grade_entries_female_non_negative"),
        sa.CheckConstraint("today_pp >= 0", name="ck_daily_grade_entries_pp_non_negative"),
        sa.CheckConstraint("today_kp >= 0", name="ck_daily_grade_entries_kp_non_negative"),
        sa.CheckConstraint("today_female <= today_total", name="ck_daily_grade_entries_female_lte_total"),
        sa.CheckConstraint(
            "today_pp + today_kp <= today_total", name="ck_daily_grade_entries_pp_kp_lte_total"
        ),
    )
    op.create_index("ix_daily_grade_entries_report_id", "daily_grade_entries", ["report_id"])

    # ---------------------------------------------- daily_totals_snapshot
    op.create_table(
        "daily_totals_snapshot",
        _uuid_pk(),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("category_id", UUID, nullable=False),
        sa.Column("cumulative_total", sa.Integer, server_default="0", nullable=False),
        sa.Column("cumulative_female", sa.Integer, server_default="0", nullable=False),
        sa.Column("cumulative_pp", sa.Integer, server_default="0", nullable=False),
        sa.Column("cumulative_kp", sa.Integer, server_default="0", nullable=False),
        sa.Column("grade_cumulative", JSONB, nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "report_date", "category_id", name="uq_daily_totals_snapshot_date_category"
        ),
    )
    op.create_index("ix_daily_totals_snapshot_report_date", "daily_totals_snapshot", ["report_date"])
    op.create_index("ix_daily_totals_snapshot_category_id", "daily_totals_snapshot", ["category_id"])


def downgrade() -> None:
    op.drop_table("daily_totals_snapshot")
    op.drop_table("daily_grade_entries")
    op.drop_table("daily_reports")
    op.drop_table("grades")
    op.drop_table("categories")
    op.drop_table("settings")
    op.drop_table("audit_logs")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
