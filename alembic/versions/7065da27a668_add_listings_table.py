"""Add listings table

Revision ID: 7065da27a668
Revises: fc8da0ebee8e
Create Date: 2026-03-23 12:24:00.107279
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7065da27a668"
down_revision: str | Sequence[str] | None = "fc8da0ebee8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("listing_id", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False, server_default=""),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("url", sa.String(1000), nullable=False, server_default=""),
        sa.Column("address", sa.String(500), nullable=False, server_default=""),
        sa.Column("neighbourhood", sa.String(100), nullable=False, server_default=""),
        sa.Column("bedrooms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("furnished", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("parking", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("move_in_date", sa.String(20), nullable=False, server_default=""),
        sa.Column("scraped_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Clear orphan seen_listings before adding FK
    op.execute(sa.text("DELETE FROM seen_listings"))

    # Add FK from seen_listings.listing_id to listings.listing_id
    op.create_foreign_key(
        "fk_seen_listings_listing_id",
        "seen_listings",
        "listings",
        ["listing_id"],
        ["listing_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_seen_listings_listing_id", "seen_listings", type_="foreignkey")
    op.drop_table("listings")
