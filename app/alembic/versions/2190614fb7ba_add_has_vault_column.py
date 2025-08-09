"""add has_vault column to users

Revision ID: 2190614fb7ba
Revises: 82e0a0e8ce04
Create Date: 2025-08-07 08:20:16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2190614fb7ba"
down_revision: Union[str, Sequence[str], None] = "c058612a8eb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("has_vault", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "has_vault")

