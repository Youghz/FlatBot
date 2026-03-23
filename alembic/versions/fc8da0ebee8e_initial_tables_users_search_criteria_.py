"""Initial tables: users, search_criteria, seen_listings

Revision ID: fc8da0ebee8e
Revises:
Create Date: 2026-03-22 23:01:50.283683
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "fc8da0ebee8e"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("telegram_chat_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )

    op.create_table(
        "search_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("neighbourhoods", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("price_min", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("price_max", sa.Integer(), nullable=False, server_default=sa.text("3000")),
        sa.Column("bedrooms_min", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("bedrooms_max", sa.Integer(), nullable=True),
        sa.Column("furnished", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("parking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("move_in_before", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "seen_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("listing_id", sa.String(255), nullable=False),
        sa.Column("notified_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "listing_id"),
    )


def downgrade() -> None:
    op.drop_table("seen_listings")
    op.drop_table("search_criteria")
    op.drop_table("users")
