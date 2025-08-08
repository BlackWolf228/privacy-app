from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.transaction import Transaction, TxType, TxStatus
from app.models.wallet import Wallet

router = APIRouter(prefix="/webhooks/circle", tags=["Circle Webhook"])

@router.post("/")
async def handle_circle_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    event_type = payload.get("type")
    data = payload.get("data", {})

    wallet_id = data.get("walletId") or data.get("source", {}).get("id")
    result = await db.execute(select(Wallet).where(Wallet.wallet_id == wallet_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        return {"ignored": True}

    amount = data.get("amount") or data.get("balance")
    amount_val = Decimal(str(amount)) if amount is not None else Decimal("0")

    status_str = (data.get("status") or data.get("state") or "").lower()
    if status_str in {"complete", "confirmed"}:
        status = TxStatus.confirmed
    elif status_str == "failed":
        status = TxStatus.failed
    elif status_str == "canceled":
        status = TxStatus.canceled
    else:
        status = TxStatus.pending

    direction = (data.get("direction") or "").upper()
    if direction == "OUT":
        tx_type = TxType.crypto_out
    else:
        tx_type = TxType.crypto_in

    tx = Transaction(
        user_id=wallet.user_id,
        wallet_id=wallet.id,
        provider="circle",
        type=tx_type,
        status=status,
        amount=amount_val,
        currency=data.get("currency") or "",
        address_from=data.get("source", {}).get("address"),
        address_to=data.get("destination", {}).get("address"),
        provider_ref_id=data.get("id"),
        tx_hash=data.get("txHash"),
        meta=payload,
    )
    db.add(tx)
    await db.commit()
    return {"received": True}
