"""seed reference data

Creates the three applicant categories, the five grades, the default system
settings and the first superadmin account.

Revision ID: 0002_reference_data
Revises: 0001_initial
Create Date: 2026-01-01 00:05:00
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_reference_data"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = [
    {
        "code": "current_year",
        "position": 1,
        "roman_numeral": "I.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបឆ្នាំ{year}",
        "description": "Applicants who graduated in the current academic year.",
    },
    {
        "code": "before_current_year",
        "position": 2,
        "roman_numeral": "II.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបមុនឆ្នាំ{year}",
        "description": "Applicants from previous academic years.",
    },
    {
        "code": "other_province",
        "position": 3,
        "roman_numeral": "III.",
        "title_template": "បានទទួលពាក្យបាក់ឌុបខេត្តផ្សេង",
        "description": "Applicants coming from other provinces.",
    },
]

GRADES = [
    ("A", 1, "ថ្នាក់ខ្ពស្តុង A"),
    ("B", 2, "ថ្នាក់ខ្ពស្តុង B"),
    ("C", 3, "ថ្នាក់ខ្ពស្តុង C"),
    ("D", 4, "ថ្នាក់ខ្ពស្តុង D"),
    ("E", 5, "ថ្នាក់ខ្ពស្តុង E"),
]

SETTINGS = [
    ("current_year", str(os.getenv("DEFAULT_CURRENT_YEAR", "2026")), "int",
     "Academic year embedded in category titles and Telegram reports.", False),
    ("institution_name", "សាលាសិក្សា", "string",
     "Institution name printed on PDF/Excel exports.", False),
    ("daily_cutoff_time", "17:00", "string",
     "Time after which a day is considered closed for reporting.", False),
    ("locale", "km-KH", "string", "Default locale for generated reports.", False),
    ("telegram_chat_id", None, "string",
     "Default Telegram chat id for daily broadcasts.", False),
    ("telegram_bot_token", None, "string",
     "Telegram bot token (stored as a secret).", True),
]


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------ categories
    for spec in CATEGORIES:
        bind.execute(
            sa.text(
                """
                INSERT INTO categories (id, code, position, roman_numeral, title_template,
                                        is_active, description, created_at, updated_at)
                VALUES (:id, :code, :position, :roman, :title, true, :description, now(), now())
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "code": spec["code"],
                "position": spec["position"],
                "roman": spec["roman_numeral"],
                "title": spec["title_template"],
                "description": spec["description"],
            },
        )

    # ---------------------------------------------------------------- grades
    for code, position, label in GRADES:
        bind.execute(
            sa.text(
                """
                INSERT INTO grades (id, code, position, label, is_active, created_at, updated_at)
                VALUES (:id, :code, :position, :label, true, now(), now())
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {"id": uuid.uuid4(), "code": code, "position": position, "label": label},
        )

    # -------------------------------------------------------------- settings
    for key, value, value_type, description, is_secret in SETTINGS:
        bind.execute(
            sa.text(
                """
                INSERT INTO settings (id, key, value, value_type, description, is_secret,
                                      created_at, updated_at)
                VALUES (:id, :key, :value, :value_type, :description, :is_secret, now(), now())
                ON CONFLICT (key) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "key": key,
                "value": value,
                "value_type": value_type,
                "description": description,
                "is_secret": is_secret,
            },
        )

    # -------------------------------------------------------- first superadmin
    email = os.getenv("FIRST_SUPERUSER_EMAIL", "admin@scholar.edu.kh")
    username = os.getenv("FIRST_SUPERUSER_USERNAME", "admin")
    password = os.getenv("FIRST_SUPERUSER_PASSWORD")
    if password:
        from app.core.security import hash_password

        bind.execute(
            sa.text(
                """
                INSERT INTO users (id, email, username, full_name, hashed_password, role,
                                   is_active, is_superuser, created_at, updated_at)
                VALUES (:id, :email, :username, 'System Administrator', :password,
                        'superadmin', true, true, now(), now())
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {
                "id": uuid.uuid4(),
                "email": email,
                "username": username,
                "password": hash_password(password),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM settings WHERE key IN ('current_year')"))
    bind.execute(sa.text("DELETE FROM grades"))
    bind.execute(sa.text("DELETE FROM categories"))
