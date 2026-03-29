"""Add published_date and surface_sqft, make furnished/parking NOT NULL

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-29 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clear all listings (re-scrape needed with new fields)
    op.execute(sa.text("DELETE FROM seen_listings"))
    op.execute(sa.text("DELETE FROM listings"))

    # Add new columns
    op.add_column("listings", sa.Column("published_date", sa.String(20), nullable=False, server_default=""))
    op.add_column("listings", sa.Column("surface_sqft", sa.Integer(), nullable=False, server_default="0"))

    # Make furnished/parking NOT NULL (no more unknown values)
    op.execute(sa.text("UPDATE listings SET furnished = false WHERE furnished IS NULL"))
    op.execute(sa.text("UPDATE listings SET parking = false WHERE parking IS NULL"))
    op.alter_column(
        "listings", "furnished", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false")
    )
    op.alter_column("listings", "parking", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false"))


def downgrade() -> None:
    op.alter_column("listings", "parking", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.alter_column("listings", "furnished", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.drop_column("listings", "surface_sqft")
    op.drop_column("listings", "published_date")
