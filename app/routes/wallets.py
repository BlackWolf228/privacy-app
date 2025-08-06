from fastapi import APIRouter
from pydantic import BaseModel

from app.services.cryptoapi import create_wallet

router = APIRouter(prefix="/wallets", tags=["Wallets"])


class WalletCreate(BaseModel):
    currency: str
    network: str


@router.post("/")
async def create_wallet_endpoint(payload: WalletCreate):
    return await create_wallet(payload.currency, payload.network)
