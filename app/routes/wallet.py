from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.wallet_log import WalletLog
from app.schemas.wallet import (
    WalletOut,
    WalletBalance,
    WithdrawalRequest,
    WithdrawalResponse,
)
from app.services.fireblocks import (
    create_vault_account,
    get_wallet_balance,
    create_transfer,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix="/wallets", tags=["Wallets"])

@router.post("/", response_model=WalletOut)
async def create_user_wallet(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    data = await create_vault_account(str(current_user.id))
    wallet = Wallet(
        user_id=current_user.id,
        wallet_id=data["vault_account_id"],
        address="",
        currency="VAULT",
        network="FIREBLOCKS",
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    log = WalletLog(
        wallet_id=wallet.wallet_id,
        network=wallet.network,
        address=wallet.address,
        balance=None,
        status="created",
        action="wallet.created",
    )
    db.add(log)
    await db.commit()
    return wallet

@router.get("/{wallet_id}/balance", response_model=WalletBalance)
async def wallet_balance(
    wallet_id: str,
    asset: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.wallet_id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    data = await get_wallet_balance(wallet.wallet_id, asset)

    log = WalletLog(
        wallet_id=wallet.wallet_id,
        network=wallet.network,
        address=wallet.address,
        balance=data.get("amount"),
        status="balance",
        action="wallet.balance.check",
    )
    db.add(log)
    await db.commit()

    return WalletBalance(wallet_id=wallet.wallet_id, amount=data["amount"], asset=data["currency"])

@router.post("/{wallet_id}/withdraw", response_model=WithdrawalResponse)
async def withdraw_from_wallet(
    wallet_id: str,
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.wallet_id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    transfer = await create_transfer(
        wallet.wallet_id, payload.asset, payload.amount, payload.address
    )

    log = WalletLog(
        wallet_id=wallet.wallet_id,
        network=wallet.network,
        address=payload.address,
        balance=payload.amount,
        status=transfer.get("status") or transfer.get("state"),
        action="wallet.withdraw",
    )
    db.add(log)
    await db.commit()

    return WithdrawalResponse(
        transfer_id=transfer.get("id", ""),
        status=transfer.get("status") or transfer.get("state", "pending"),
    )
