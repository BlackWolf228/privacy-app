"""add vaults table and update wallets

Revision ID: 582c39d1f35a
Revises: 0700c6c27ae3
Create Date: 2025-08-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '582c39d1f35a'
down_revision: Union[str, Sequence[str], None] = '0700c6c27ae3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'vaults',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vault_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vault_id')
    )
    op.create_index(op.f('ix_vaults_id'), 'vaults', ['id'], unique=False)

    op.add_column('wallets', sa.Column('vault_id', sa.String(), nullable=False))
    op.create_foreign_key(None, 'wallets', 'vaults', ['vault_id'], ['vault_id'])
    op.drop_column('wallets', 'wallet_id')

    op.add_column('wallet_logs', sa.Column('vault_id', sa.String(), nullable=False))
    op.create_foreign_key(None, 'wallet_logs', 'vaults', ['vault_id'], ['vault_id'])
    op.drop_column('wallet_logs', 'wallet_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('wallet_logs', sa.Column('wallet_id', sa.String(), nullable=False))
    op.drop_constraint(None, 'wallet_logs', type_='foreignkey')
    op.drop_column('wallet_logs', 'vault_id')

    op.add_column('wallets', sa.Column('wallet_id', sa.String(), nullable=False))
    op.drop_constraint(None, 'wallets', type_='foreignkey')
    op.drop_column('wallets', 'vault_id')

    op.drop_index(op.f('ix_vaults_id'), table_name='vaults')
    op.drop_table('vaults')

