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
    amount: str
    asset: str

class WithdrawalRequest(BaseModel):
    address: str
    amount: str
    asset: str


class InternalTransferRequest(BaseModel):
    destination_vault_id: str
    amount: str
    asset: str

class WithdrawalResponse(BaseModel):
    transfer_id: str
    status: str
