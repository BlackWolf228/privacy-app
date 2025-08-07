"""Make privacy_id non-nullable

Revision ID: c058612a8eb3
Revises: 4a0b3c8f3a1d
Create Date: 2025-08-07 07:59:26.495250

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c058612a8eb3'
down_revision: Union[str, Sequence[str], None] = '4a0b3c8f3a1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'privacy_id', nullable=False)

def downgrade() -> None:
    op.alter_column('users', 'privacy_id', nullable=True)
