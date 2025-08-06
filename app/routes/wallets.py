from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/wallets", tags=["Wallets"])


class WalletCreate(BaseModel):
    currency: str
    network: str


async def create_wallet(currency: str, network: str):
    """Stub wallet creation function."""
    return {"currency": currency, "network": network}


@router.post("/")
async def create_wallet_endpoint(payload: WalletCreate):
    return await create_wallet(payload.currency, payload.network)
