"""add privacy id and username

Revision ID: 4a0b3c8f3a1d
Revises: 2190614fb7ba
Create Date: 2025-03-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4a0b3c8f3a1d'
down_revision = '2190614fb7ba'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('privacy_id', sa.String(length=10), nullable=True))
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_privacy_id', 'users', ['privacy_id'])
    op.create_unique_constraint('uq_users_username', 'users', ['username'])
    op.create_check_constraint(
        'ck_privacy_id_username_diff',
        'users',
        'username IS NULL OR privacy_id <> username'
    )


def downgrade() -> None:
    op.drop_constraint('ck_privacy_id_username_diff', 'users', type_='check')
    op.drop_constraint('uq_users_username', 'users', type_='unique')
    op.drop_constraint('uq_users_privacy_id', 'users', type_='unique')
    op.drop_column('users', 'username')
    op.drop_column('users', 'privacy_id')
