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


class FeeEstimateRequest(BaseModel):
    vault_id: str
    asset: str
    amount: str


class FeeEstimateResponse(BaseModel):
    low: str | None = None
    medium: str | None = None
    high: str | None = None
