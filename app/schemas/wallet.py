from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel

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
