"""create wallets table

Revision ID: c3a6b7d1e8f9
Revises: 7f1bfbb977c2
Create Date: 2025-08-15 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3a6b7d1e8f9'
down_revision: Union[str, Sequence[str], None] = '7f1bfbb977c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'wallets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('wallet_id', sa.String(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('network', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'currency', 'network', name='uix_user_currency_network')
    )
    op.create_index(op.f('ix_wallets_id'), 'wallets', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_wallets_id'), table_name='wallets')
    op.drop_table('wallets')
