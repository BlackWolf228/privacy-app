"""Add transactions and webhook_events tables

Revision ID: 13d9e5c7f4b2
Revises: 0700c6c27ae3
Create Date: 2025-08-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '13d9e5c7f4b2'
down_revision: Union[str, Sequence[str], None] = "2190614fb7ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    tx_type_enum = postgresql.ENUM(
        'crypto_in', 'crypto_out', 'internal_in', 'internal_out', 'fiat_in', 'fiat_out', 'swap',
        name='tx_type',
        create_type=False
    )
    tx_type_enum.create(op.get_bind(), checkfirst=True)

    tx_status_enum = postgresql.ENUM(
        'pending', 'confirmed', 'failed', 'canceled',
        name='tx_status',
        create_type=False
    )
    tx_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('wallet_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('type', tx_type_enum, nullable=False),
        sa.Column('status', tx_status_enum, nullable=False, server_default=sa.text("'pending'::tx_status")),
        sa.Column('amount', sa.Numeric(38, 18), nullable=False),
        sa.Column('currency', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('fee_amount', sa.Numeric(38, 18), nullable=True),
        sa.Column('fee_currency', sa.String(), nullable=True),
        sa.Column('balance_after', sa.Numeric(38, 18), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('group_id', sa.UUID(), nullable=True),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('provider_ref_id', sa.String(), nullable=True),
        sa.Column('chain', sa.String(), nullable=True),
        sa.Column('tx_hash', sa.String(), nullable=True),
        sa.Column('address_from', sa.String(), nullable=True),
        sa.Column('address_to', sa.String(), nullable=True),
        sa.Column('counterparty_user', sa.UUID(), nullable=True),
        sa.Column('iban_from', sa.String(), nullable=True),
        sa.Column('iban_to', sa.String(), nullable=True),
        sa.Column('payment_method', sa.String(), nullable=True),
        sa.Column('merchant_name', sa.String(), nullable=True),
        sa.Column('card_last4', sa.String(), nullable=True),
        sa.Column('original_amount', sa.Numeric(38, 18), nullable=True),
        sa.Column('original_currency', sa.String(), nullable=True),
        sa.Column('fx_rate', sa.Numeric(38, 18), nullable=True),
        sa.Column('pay_amount', sa.Numeric(38, 18), nullable=True),
        sa.Column('pay_currency', sa.String(), nullable=True),
        sa.Column('receive_amount', sa.Numeric(38, 18), nullable=True),
        sa.Column('receive_currency', sa.String(), nullable=True),
        sa.Column('meta', postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ),
        sa.ForeignKeyConstraint(['counterparty_user'], ['users.id'], ),
    )
    op.create_index('ix_transactions_user_created', 'transactions', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_transactions_wallet_created', 'transactions', ['wallet_id', 'created_at'], unique=False)
    op.create_index('ix_transactions_provider_ref', 'transactions', ['provider', 'provider_ref_id'], unique=False)
    op.create_index('ix_transactions_group_id', 'transactions', ['group_id'], unique=False)
    op.create_index('ix_transactions_type_status', 'transactions', ['type', 'status'], unique=False)

    op.create_table(
        'webhook_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('provider_ref_id', sa.String(), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('webhook_events')
    op.drop_index('ix_transactions_type_status', table_name='transactions')
    op.drop_index('ix_transactions_group_id', table_name='transactions')
    op.drop_index('ix_transactions_provider_ref', table_name='transactions')
    op.drop_index('ix_transactions_wallet_created', table_name='transactions')
    op.drop_index('ix_transactions_user_created', table_name='transactions')
    op.drop_table('transactions')
    tx_status_enum = postgresql.ENUM(name='tx_status')
    tx_status_enum.drop(op.get_bind(), checkfirst=True)
    tx_type_enum = postgresql.ENUM(name='tx_type')
    tx_type_enum.drop(op.get_bind(), checkfirst=True)
