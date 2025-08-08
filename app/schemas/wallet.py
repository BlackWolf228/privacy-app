from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class WalletOut(BaseModel):
    id: UUID
    wallet_id: str
    address: str
    currency: str
    network: str
    created_at: datetime

    class Config:
        from_attributes = True

class WalletBalance(BaseModel):
    wallet_id: str
    amount: str
    asset: str

class WithdrawalRequest(BaseModel):
    address: str
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
