from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.transaction import Transaction, TxType, TxStatus
from app.schemas.wallet import (
    WalletCreate,
    WalletOut,
    WalletBalance,
    ExternalTransferRequest,
    ExternalTransferResponse,
    InternalTransferRequest,
    TransactionResponse,
)
from app.services.circle import (
    SUPPORTED_NETWORKS,
    create_wallet,
    get_wallet_balance,
    create_transfer,
)
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

@router.get("/{wallet_id}/balance", response_model=WalletBalance)
async def wallet_balance(
    wallet_id: str,
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

    data = await get_wallet_balance(wallet.wallet_id)

    return WalletBalance(wallet_id=wallet.wallet_id, amount=data["amount"], currency=data["currency"])


@router.post("/{wallet_id}/internal", response_model=TransactionResponse)
async def internal_transfer(
    wallet_id: str,
    payload: InternalTransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.wallet_id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    from_wallet = result.scalar_one_or_none()
    if from_wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    result = await db.execute(select(Wallet).where(Wallet.wallet_id == payload.to_wallet_id))
    to_wallet = result.scalar_one_or_none()
    if to_wallet is None:
        raise HTTPException(status_code=404, detail="Destination wallet not found")

    if from_wallet.currency != to_wallet.currency or from_wallet.network != to_wallet.network:
        raise HTTPException(status_code=400, detail="Mismatched currency or network")

    amount = payload.amount

    tx_out = Transaction(
        user_id=current_user.id,
        wallet_id=from_wallet.id,
        provider="baas",
        type=TxType.internal_out,
        status=TxStatus.confirmed,
        amount=amount,
        currency=from_wallet.currency,
        address_to=to_wallet.address,
        counterparty_user=to_wallet.user_id,
    )

    tx_in = Transaction(
        user_id=to_wallet.user_id,
        wallet_id=to_wallet.id,
        provider="baas",
        type=TxType.internal_in,
        status=TxStatus.confirmed,
        amount=amount,
        currency=to_wallet.currency,
        address_from=from_wallet.address,
        counterparty_user=current_user.id,
    )

    db.add_all([tx_out, tx_in])
    await db.commit()
    await db.refresh(tx_out)

    return TransactionResponse(transaction_id=tx_out.id, status=tx_out.status.value)


@router.post("/{wallet_id}/external-transfer", response_model=ExternalTransferResponse)
async def external_transfer(
    wallet_id: str,
    payload: ExternalTransferRequest,
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

    transfer = await create_transfer(wallet.wallet_id, payload.address, payload.amount, wallet.network)

    state = (transfer.get("state") or "").lower()
    status = (
        TxStatus.confirmed
        if state == "complete"
        else TxStatus.failed if state == "failed" else TxStatus.pending
    )

    transaction = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        provider="baas",
        type=TxType.crypto_out,
        status=status,
        amount=payload.amount,
        currency=wallet.currency,
        address_to=payload.address,
        provider_ref_id=transfer.get("id"),
        chain=wallet.network,
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    return ExternalTransferResponse(
        transaction_id=transaction.id,
        transfer_id=transfer.get("id", ""),
        status=transaction.status.value,
    )
