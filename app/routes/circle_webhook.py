from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.wallet_log import WalletLog

router = APIRouter(prefix="/webhooks/circle", tags=["Circle Webhook"])

@router.post("/")
async def handle_circle_webhook(payload: dict, db: AsyncSession = Depends(get_db)):
    event_type = payload.get("type")
    data = payload.get("data", {})

    wallet_id = data.get("walletId") or data.get("source", {}).get("id")
    network = data.get("blockchain") or data.get("source", {}).get("chain")
    address = data.get("address") or data.get("destination", {}).get("address")
    balance = data.get("amount") or data.get("balance")
    status = data.get("status") or data.get("state")

    log = WalletLog(
        wallet_id=wallet_id or "",
        network=network or "",
        address=address or "",
        balance=str(balance) if balance is not None else None,
        status=status,
        action=event_type or "",
    )
    db.add(log)
    await db.commit()
    return {"received": True}
