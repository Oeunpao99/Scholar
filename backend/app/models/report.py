"""Daily reports, per-grade entries and cumulative snapshots."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.models.enums import CategoryCode, GradeLetter

if TYPE_CHECKING:
    from app.models.user import User

_NON_NEGATIVE = "{column} >= 0"


class DailyReport(Base, TimestampMixin):
    """Staff enter ONLY today's gain for a category. Cumulative values are derived."""

    __tablename__ = "daily_reports"
    __table_args__ = (
        UniqueConstraint("report_date", "category_id", name="uq_daily_reports_date_category"),
        CheckConstraint("today_total >= 0", name="ck_daily_reports_today_total_non_negative"),
        CheckConstraint("today_female >= 0", name="ck_daily_reports_today_female_non_negative"),
        CheckConstraint("today_pp >= 0", name="ck_daily_reports_today_pp_non_negative"),
        CheckConstraint("today_kp >= 0", name="ck_daily_reports_today_kp_non_negative"),
        CheckConstraint("today_female <= today_total", name="ck_daily_reports_female_lte_total"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    today_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_female: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_pp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_kp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", server_default="manual"
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )

    category: Mapped["Category"] = relationship(lazy="joined")  # noqa: F821
    created_by_user: Mapped["User | None"] = relationship(
        back_populates="reports", foreign_keys=[created_by], lazy="joined"
    )
    entries: Mapped[list[DailyGradeEntry]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DailyGradeEntry.position",
    )

    @property
    def grade_sum_total(self) -> int:
        return sum(e.today_total for e in self.entries)

    @property
    def grade_sum_female(self) -> int:
        return sum(e.today_female for e in self.entries)

    @property
    def grade_sum_pp(self) -> int:
        return sum(e.today_pp for e in self.entries)

    @property
    def grade_sum_kp(self) -> int:
        return sum(e.today_kp for e in self.entries)

    @property
    def is_grade_consistent(self) -> bool:
        return (
            self.grade_sum_total == self.today_total
            and self.grade_sum_female == self.today_female
            and self.grade_sum_pp == self.today_pp
            and self.grade_sum_kp == self.today_kp
        )


class DailyGradeEntry(Base):
    """One row per grade inside a daily report (today's gain only)."""

    __tablename__ = "daily_grade_entries"
    __table_args__ = (
        UniqueConstraint("report_id", "grade", name="uq_daily_grade_entries_report_grade"),
        CheckConstraint("grade in ('A','B','C','D','E')", name="ck_daily_grade_entries_grade_letter"),
        CheckConstraint("today_total >= 0", name="ck_daily_grade_entries_total_non_negative"),
        CheckConstraint("today_female >= 0", name="ck_daily_grade_entries_female_non_negative"),
        CheckConstraint("today_pp >= 0", name="ck_daily_grade_entries_pp_non_negative"),
        CheckConstraint("today_kp >= 0", name="ck_daily_grade_entries_kp_non_negative"),
        CheckConstraint("today_female <= today_total", name="ck_daily_grade_entries_female_lte_total"),
        CheckConstraint(
            "today_pp + today_kp <= today_total", name="ck_daily_grade_entries_pp_kp_lte_total"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    grade: Mapped[str] = mapped_column(
        String(8), nullable=False, default=GradeLetter.D, server_default="D"
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=4, server_default="4")
    today_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_female: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_pp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    today_kp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    report: Mapped[DailyReport] = relationship(back_populates="entries", lazy="joined")

    @property
    def has_gain(self) -> bool:
        return bool(self.today_total or self.today_female or self.today_pp or self.today_kp)


class DailyTotalsSnapshot(Base):
    """
    Materialised cumulative totals per (report_date, category).

    Kept in sync with the source rows so dashboards never scan the whole
    history, and so a report can be rendered as a point-in-time statement.
    """

    __tablename__ = "daily_totals_snapshot"
    __table_args__ = (
        UniqueConstraint("report_date", "category_id", name="uq_daily_totals_snapshot_date_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cumulative_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cumulative_female: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cumulative_pp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cumulative_kp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    grade_cumulative: Mapped[dict | None] = mapped_column("grade_cumulative", JSONB)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    category: Mapped["Category"] = relationship(lazy="joined")  # noqa: F821

    def grade_value(self, grade: str, metric: str = "total") -> int:
        if not self.grade_cumulative:
            return 0
        return int(self.grade_cumulative.get(grade, {}).get(metric, 0))
