"""Add telegram_link_code to users

Revision ID: 29991f863489
Revises: 7065da27a668
Create Date: 2026-03-23 18:09:19.589900
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "29991f863489"
down_revision: str | Sequence[str] | None = "7065da27a668"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_link_code", sa.String(10), nullable=True, unique=True))
    op.create_index("ix_users_telegram_link_code", "users", ["telegram_link_code"])


def downgrade() -> None:
    op.drop_index("ix_users_telegram_link_code", "users")
    op.drop_column("users", "telegram_link_code")
