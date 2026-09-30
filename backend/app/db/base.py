"""Declarative base, shared column types and naming conventions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit constraint names keep Alembic autogenerate deterministic.
# Checks are named explicitly in the models, so the convention only has to
# cover unnamed ones without double-prefixing the "ck_" that is already there.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Timezone-aware UTC now, matching what ``timestamptz`` columns carry."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def to_dict(self) -> dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={pk}>"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # ``onupdate`` is a Python callable rather than ``func.now()`` on purpose.
    # A SQL-expression onupdate forces SQLAlchemy to expire the attribute after
    # every UPDATE, and reading an expired attribute triggers synchronous IO -
    # which raises MissingGreenlet in async code.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
