"""Clear seen_listings after notification bug fix

Listings were marked as seen without being notified.
Clear seen_listings so users get notified on next scrape cycle.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-28 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | Sequence[str] | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM seen_listings"))


def downgrade() -> None:
    # Data cannot be restored — this is intentionally irreversible
    pass
