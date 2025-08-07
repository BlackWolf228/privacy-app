from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.wallet_log import WalletLog
from app.models.vault import Vault
from app.schemas.wallet import WalletOut, WalletBalance, WithdrawalRequest, WithdrawalResponse
from app.utils.auth import get_current_user
from app.services.fireblocks import create_vault_account, generate_address_for_vault

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/vault")
async def create_user_vault(
    asset: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Fireblocks vault for the current user.

    If the user already has a vault, an HTTP 400 error is raised. Otherwise a new
    vault is created via the Fireblocks service and persisted along with the
    updated user flag.
    """

    if current_user.has_vault:
        raise HTTPException(status_code=400, detail="User already has a vault")

    data = await create_vault_account(str(current_user.id), asset)
    vault = Vault(vault_id=data["vault_account_id"], user_id=current_user.id)

    current_user.has_vault = True
    db.add(vault)
    db.add(current_user)
    await db.commit()
    await db.refresh(vault)

    return vault


@router.post("/", response_model=WalletOut)
async def create_user_wallet(
    asset: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    # Check if wallet for this asset already exists
    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == current_user.id,
            Wallet.currency == asset,
            Wallet.network == "FIREBLOCKS",
        )
    )
    existing_wallet = result.scalar_one_or_none()
    if existing_wallet:
        return existing_wallet

    # Fetch or create the user's vault
    result = await db.execute(select(Vault).where(Vault.user_id == current_user.id))
    vault = result.scalar_one_or_none()

    if vault is None:
        vault_data = await create_vault_account(str(current_user.id), asset)
        vault = Vault(vault_id=vault_data["vault_account_id"], user_id=current_user.id)
        address = vault_data["address"]
        db.add(vault)
        await db.commit()
        await db.refresh(vault)
    else:
        address = await generate_address_for_vault(vault.vault_id, asset)

    wallet = Wallet(
        user_id=current_user.id,
        vault_id=vault.vault_id,
        address=address,
        currency=asset,
        network="FIREBLOCKS",
    )
    db.add(wallet)
    await db.commit()
    await db.refresh(wallet)

    log = WalletLog(
        vault_id=vault.vault_id,
        network="FIREBLOCKS",
        address=address,
        balance=None,
        status="created",
        action="wallet.created",
    )
    db.add(log)
    await db.commit()

    return wallet


@router.get("/{vault_id}/balance", response_model=WalletBalance)
async def wallet_balance(
    vault_id: str,
    asset: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.vault_id == vault_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    data = await get_wallet_balance(wallet.vault_id, asset)

    log = WalletLog(
        vault_id=wallet.vault_id,
        network=wallet.network,
        address=wallet.address,
        balance=data.get("amount"),
        status="balance",
        action="wallet.balance.check",
    )
    db.add(log)
    await db.commit()

    return WalletBalance(vault_id=wallet.vault_id, amount=data["amount"], asset=data["currency"])


@router.post("/{vault_id}/withdraw", response_model=WithdrawalResponse)
async def withdraw_from_wallet(
    vault_id: str,
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Wallet).where(
            Wallet.vault_id == vault_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    transfer = await create_transfer(
        wallet.vault_id, payload.asset, payload.amount, payload.address
    )

    log = WalletLog(
        vault_id=wallet.vault_id,
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
