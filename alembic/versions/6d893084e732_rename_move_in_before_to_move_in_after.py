"""Rename move_in_before to move_in_after

Revision ID: 6d893084e732
Revises: 29991f863489
Create Date: 2026-03-25 19:08:29.096846
"""

from collections.abc import Sequence

from alembic import op

revision: str = "6d893084e732"
down_revision: str | Sequence[str] | None = "29991f863489"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("search_criteria", "move_in_before", new_column_name="move_in_after")


def downgrade() -> None:
    op.alter_column("search_criteria", "move_in_after", new_column_name="move_in_before")
