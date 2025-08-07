from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.wallet import Wallet
from app.models.wallet_log import WalletLog
from app.models.vault import Vault
from app.schemas.wallet import (
    WalletOut,
    WalletBalance,
    WithdrawalRequest,
    WithdrawalResponse,
    InternalTransferRequest,
)
from app.utils.auth import get_current_user
from app.services.fireblocks import (
    create_vault_account,
    create_asset_for_vault,
    generate_address_for_vault,
    get_wallet_balance,
    create_transfer,
    transfer_between_vault_accounts,
    AssetAlreadyExistsError,
)

router = APIRouter(prefix="/wallets", tags=["Wallets"])


@router.post("/vault")
async def create_user_vault(
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

    data = await create_vault_account(str(current_user.id))
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
        vault_data = await create_vault_account(str(current_user.id))
        vault = Vault(vault_id=vault_data["vault_account_id"], user_id=current_user.id)
        current_user.has_vault = True
        db.add(vault)
        db.add(current_user)
        await db.commit()
        await db.refresh(vault)

    try:
        address = await create_asset_for_vault(vault.vault_id, asset)
    except AssetAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409,
            detail="asset already provisioned for this vault",
        ) from exc

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


@router.get("/{wallet_id}/balance", response_model=WalletBalance)
async def wallet_balance(
    wallet_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the balance for a specific wallet identified by its internal ID."""
    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    data = await get_wallet_balance(wallet.vault_id, wallet.currency)

    log = WalletLog(
        vault_id=wallet.vault_id,
        network=wallet.network,
        address=wallet.address,
        balance=data.get("balance"),
        status="balance",
        action="wallet.balance.check",
    )
    db.add(log)
    await db.commit()

    return WalletBalance(
        wallet_id=wallet.id,
        balance=data["balance"],
        asset=data["asset"],
        pending_balance=data.get("pending_balance"),
        available_balance=data.get("available_balance"),
    )


@router.post("/{wallet_id}/transfer", response_model=WithdrawalResponse)
async def transfer_between_wallets(
    wallet_id: UUID,
    payload: InternalTransferRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer funds to another user's wallet identified by privacy ID or username."""
    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if payload.asset != wallet.currency:
        raise HTTPException(status_code=400, detail="Asset mismatch with wallet")

    # Locate destination user by privacy ID or username
    result = await db.execute(
        select(User).where(User.privacy_id == payload.destination_user_id)
    )
    dest_user = result.scalar_one_or_none()
    if dest_user is None:
        result = await db.execute(
            select(User).where(User.username == payload.destination_user_id)
        )
        dest_user = result.scalar_one_or_none()
    if dest_user is None:
        raise HTTPException(status_code=404, detail="Destination user not found")

    # Find or create destination wallet for the requested asset
    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == dest_user.id,
            Wallet.currency == payload.asset,
            Wallet.network == "FIREBLOCKS",
        )
    )
    dest_wallet = result.scalar_one_or_none()

    if dest_wallet is None:
        # Ensure destination user has a vault
        result = await db.execute(select(Vault).where(Vault.user_id == dest_user.id))
        dest_vault = result.scalar_one_or_none()
        if dest_vault is None:
            vault_data = await create_vault_account(str(dest_user.id))
            dest_vault = Vault(vault_id=vault_data["vault_account_id"], user_id=dest_user.id)
            dest_user.has_vault = True
            db.add(dest_vault)
            db.add(dest_user)
            await db.commit()
            await db.refresh(dest_vault)
        try:
            address = await create_asset_for_vault(dest_vault.vault_id, payload.asset)
        except AssetAlreadyExistsError:
            address = await generate_address_for_vault(dest_vault.vault_id, payload.asset)
        dest_wallet = Wallet(
            user_id=dest_user.id,
            vault_id=dest_vault.vault_id,
            address=address,
            currency=payload.asset,
            network="FIREBLOCKS",
        )
        db.add(dest_wallet)
        await db.commit()
        await db.refresh(dest_wallet)

    transfer = await transfer_between_vault_accounts(
        wallet.vault_id, dest_wallet.vault_id, payload.asset, payload.amount
    )

    log = WalletLog(
        vault_id=wallet.vault_id,
        network=wallet.network,
        address=dest_wallet.address,
        balance=payload.amount,
        status=transfer.get("status") or transfer.get("state"),
        action="wallet.transfer.internal",
    )
    db.add(log)
    await db.commit()

    return WithdrawalResponse(
        transfer_id=transfer.get("id", ""),
        status=transfer.get("status") or transfer.get("state", "pending"),
    )


@router.post("/{wallet_id}/withdraw", response_model=WithdrawalResponse)
async def withdraw_from_wallet(
    wallet_id: UUID,
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Withdraw funds from a specific wallet using its internal ID."""
    result = await db.execute(
        select(Wallet).where(
            Wallet.id == wallet_id,
            Wallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if payload.asset != wallet.currency:
        raise HTTPException(status_code=400, detail="Asset mismatch with wallet")

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
