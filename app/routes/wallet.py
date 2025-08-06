from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.wallet import WalletCreate, WalletOut
from app.services.cryptoapi import SUPPORTED_NETWORKS, create_wallet
from app.utils.auth import get_current_user

router = APIRouter(prefix="/wallets", tags=["Wallets"])

@router.post("/", response_model=WalletOut)
async def create_user_wallet(
    payload: WalletCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    currency = payload.currency.upper()
    if currency not in SUPPORTED_NETWORKS:
        raise HTTPException(status_code=400, detail="Unsupported currency")

    networks = SUPPORTED_NETWORKS[currency]
    network = payload.network.upper() if payload.network else None
    if network is None:
        if len(networks) == 1:
            network = networks[0]
        else:
            raise HTTPException(status_code=400, detail="Network required for this currency")
    elif network not in networks:
        raise HTTPException(status_code=400, detail="Unsupported network")

    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == current_user.id,
            Wallet.currency == currency,
            Wallet.network == network,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    data = await create_wallet(currency, network)
    wallet = Wallet(
        user_id=current_user.id,
        wallet_id=data["wallet_id"],
        address=data["address"],
        currency=currency,
        network=network,
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)
    return wallet
