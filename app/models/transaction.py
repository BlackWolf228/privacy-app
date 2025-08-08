from sqlalchemy import Column, String, DateTime, Enum, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from enum import Enum as PyEnum
import uuid
from datetime import datetime

from app.database import Base


class TxType(PyEnum):
    """Types of transactions supported by the system."""

    crypto_in = "crypto_in"
    crypto_out = "crypto_out"
    internal_in = "internal_in"
    internal_out = "internal_out"
    fiat_in = "fiat_in"
    fiat_out = "fiat_out"
    swap = "swap"


class TxStatus(PyEnum):
    """Lifecycle status for a transaction."""

    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"
    canceled = "canceled"


class Transaction(Base):
    """Unified table storing any transaction visible to a user."""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("wallets.id"), nullable=True)
    provider = Column(String, nullable=False)  # 'fireblocks' | 'baas' | 'system'
    type = Column(Enum(TxType, name="tx_type"), nullable=False)
    status = Column(Enum(TxStatus, name="tx_status"), default=TxStatus.pending, nullable=False)

    amount = Column(Numeric(38, 18), nullable=False)
    currency = Column(String, nullable=False)

    description = Column(String)
    fee_amount = Column(Numeric(38, 18))
    fee_currency = Column(String)
    balance_after = Column(Numeric(38, 18))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    group_id = Column(UUID(as_uuid=True))
    idempotency_key = Column(String)
    provider_ref_id = Column(String)

    chain = Column(String)
    tx_hash = Column(String)
    address_from = Column(String)
    address_to = Column(String)
    counterparty_user = Column(UUID(as_uuid=True), ForeignKey("users.id"))

    iban_from = Column(String)
    iban_to = Column(String)
    payment_method = Column(String)
    merchant_name = Column(String)
    card_last4 = Column(String)
    original_amount = Column(Numeric(38, 18))
    original_currency = Column(String)
    fx_rate = Column(Numeric(38, 18))

    pay_amount = Column(Numeric(38, 18))
    pay_currency = Column(String)
    receive_amount = Column(Numeric(38, 18))
    receive_currency = Column(String)

    meta = Column(JSONB, default=dict, nullable=False)

    # Index definitions mirror the SQL from the specification
    __table_args__ = (
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index("ix_transactions_wallet_created", "wallet_id", "created_at"),
        Index("ix_transactions_provider_ref", "provider", "provider_ref_id"),
        Index("ix_transactions_group_id", "group_id"),
        Index("ix_transactions_type_status", "type", "status"),
    )

