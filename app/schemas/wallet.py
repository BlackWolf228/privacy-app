from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class WalletOut(BaseModel):
    id: UUID
    vault_id: str
    address: str
    currency: str
    network: str
    created_at: datetime

    class Config:
        from_attributes = True

class WalletBalance(BaseModel):
    wallet_id: UUID
    balance: str
    asset: str
    pending_balance: str | None = None
    available_balance: str | None = None

class WithdrawalRequest(BaseModel):
    address: str
    amount: str
    asset: str


class InternalTransferRequest(BaseModel):
    destination_user_id: str
    amount: str
    asset: str


class DonationRequest(BaseModel):
    amount: str
    asset: str

class WithdrawalResponse(BaseModel):
    transfer_id: str
    status: str


class InternalTransferRequest(BaseModel):
    receiver_id: UUID
    amount: str
    currency: str
    description: str | None = None


class InternalTransferResponse(BaseModel):
    group_id: UUID
    sender_transaction_id: UUID
    receiver_transaction_id: UUID
