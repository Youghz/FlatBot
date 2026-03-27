"""Make furnished and parking nullable for tri-state detection

Revision ID: a1b2c3d4e5f6
Revises: 6d893084e732
Create Date: 2026-03-27 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "6d893084e732"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("listings", "furnished", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("listings", "parking", existing_type=sa.Boolean(), nullable=True)
    # Convert old False values to NULL (unknown) since we can't distinguish
    # "verified not furnished" from "no info available" in historical data
    op.execute(sa.text("UPDATE listings SET furnished = NULL WHERE furnished = false"))
    op.execute(sa.text("UPDATE listings SET parking = NULL WHERE parking = false"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE listings SET furnished = false WHERE furnished IS NULL"))
    op.execute(sa.text("UPDATE listings SET parking = false WHERE parking IS NULL"))
    op.alter_column("listings", "furnished", existing_type=sa.Boolean(), nullable=False)
    op.alter_column("listings", "parking", existing_type=sa.Boolean(), nullable=False)
