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
        orm_mode = True

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
