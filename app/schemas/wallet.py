from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, condecimal, constr

class WalletCreate(BaseModel):
    currency: str
    network: Optional[str] = None

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
    currency: str

class ExternalTransferRequest(BaseModel):
    address: constr(min_length=1)
    amount: condecimal(gt=0)

class InternalTransferRequest(BaseModel):
    to_wallet_id: constr(min_length=1)
    amount: condecimal(gt=0)

class TransactionResponse(BaseModel):
    transaction_id: UUID
    status: str


class ExternalTransferResponse(TransactionResponse):
    transfer_id: str
