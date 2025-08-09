from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID, uuid4
from decimal import Decimal

from app.database import get_db
from app.config import settings
from app.models.user import User
from app.models.wallet import Wallet
from app.models.vault import Vault
from app.models.transaction import Transaction, TxType, TxStatus

from app.schemas.wallet import (
    WalletOut,
    WalletBalance,
    WithdrawalRequest,
    WithdrawalResponse,
    InternalTransferRequest,
    DonationRequest,
    FeeEstimateRequest,
    FeeEstimateResponse,
)
from app.utils.auth import get_current_user
from app.services.fireblocks import (
    create_vault_account,
    create_asset_for_vault,
    generate_address_for_vault,
    get_wallet_balance,
    create_transfer,
    transfer_between_vault_accounts,
    estimate_transaction_fee,
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

    return WalletBalance(
        wallet_id=wallet.id,
        balance=data["balance"],
        asset=data["asset"],
        pending_balance=data.get("pending_balance"),
        available_balance=data.get("available_balance"),
    )


@router.post("/estimate_fee", response_model=FeeEstimateResponse)
async def estimate_fee(
    payload: FeeEstimateRequest,
    current_user: User = Depends(get_current_user),
):
    """Return network fee estimates for an external transfer."""
    if not current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email not verified")

    return await estimate_transaction_fee(
        payload.vault_id, payload.asset, payload.amount
    )



@router.post("/{wallet_id}/internal_transfer", response_model=WithdrawalResponse)
async def internal_transfer(
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
    if not dest_user.email_verified:
        raise HTTPException(status_code=400, detail="Destination email not verified")

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

    # Retrieve current balances to calculate balance_after fields
    sender_balance_data = await get_wallet_balance(wallet.vault_id, payload.asset)
    dest_balance_data = await get_wallet_balance(dest_wallet.vault_id, payload.asset)

    transfer = await transfer_between_vault_accounts(
        wallet.vault_id, dest_wallet.vault_id, payload.asset, payload.amount
    )

    group_id = uuid4()
    amount_dec = Decimal(payload.amount)
    sender_balance = Decimal(sender_balance_data["balance"]) - amount_dec
    dest_balance = Decimal(dest_balance_data["balance"]) + amount_dec

    tx_out = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        provider="fireblocks",
        type=TxType.internal_out,
        status=TxStatus.pending,
        amount=payload.amount,
        currency=payload.asset,
        fee_amount=Decimal("0"),
        fee_currency=payload.asset,
        balance_after=sender_balance,
        address_from=wallet.address,
        address_to=dest_wallet.address,
        counterparty_user=dest_user.id,
        provider_ref_id=transfer.get("id"),
        group_id=group_id,
    )
    tx_in = Transaction(
        user_id=dest_user.id,
        wallet_id=dest_wallet.id,
        provider="fireblocks",
        type=TxType.internal_in,
        status=TxStatus.pending,
        amount=payload.amount,
        currency=payload.asset,
        fee_amount=Decimal("0"),
        fee_currency=payload.asset,
        balance_after=dest_balance,
        address_from=wallet.address,
        address_to=dest_wallet.address,
        counterparty_user=current_user.id,
        provider_ref_id=transfer.get("id"),
        group_id=group_id,
    )

    db.add_all([tx_out, tx_in])
    await db.commit()
    await db.refresh(tx_out)

    return WithdrawalResponse(
        transfer_id=transfer.get("id", ""),
        status=transfer.get("status") or transfer.get("state", "pending"),
    )

@router.post("/{wallet_id}/donate", response_model=WithdrawalResponse)
async def donate(
    wallet_id: UUID,
    payload: DonationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Donate funds from a user's wallet to the configured donation account."""

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

    if not settings.DONATION_PRIVACY_ID:
        raise HTTPException(status_code=500, detail="Donation destination not configured")

    result = await db.execute(
        select(User).where(User.privacy_id == settings.DONATION_PRIVACY_ID)
    )
    dest_user = result.scalar_one_or_none()
    if dest_user is None:
        raise HTTPException(status_code=404, detail="Donation user not found")

    result = await db.execute(
        select(Wallet).where(
            Wallet.user_id == dest_user.id,
            Wallet.currency == payload.asset,
            Wallet.network == "FIREBLOCKS",
        )
    )
    dest_wallet = result.scalar_one_or_none()

    if dest_wallet is None:
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

    sender_balance_data = await get_wallet_balance(wallet.vault_id, payload.asset)
    dest_balance_data = await get_wallet_balance(dest_wallet.vault_id, payload.asset)

    transfer = await transfer_between_vault_accounts(
        wallet.vault_id, dest_wallet.vault_id, payload.asset, payload.amount
    )

    group_id = uuid4()
    amount_dec = Decimal(payload.amount)
    sender_balance = Decimal(sender_balance_data["balance"]) - amount_dec
    dest_balance = Decimal(dest_balance_data["balance"]) + amount_dec

    tx_out = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        provider="fireblocks",
        type=TxType.internal_out,
        status=TxStatus.pending,
        amount=payload.amount,
        currency=payload.asset,
        fee_amount=Decimal("0"),
        fee_currency=payload.asset,
        balance_after=sender_balance,
        address_from=wallet.address,
        address_to=dest_wallet.address,
        counterparty_user=dest_user.id,
        provider_ref_id=transfer.get("id"),
        group_id=group_id,
    )
    tx_in = Transaction(
        user_id=dest_user.id,
        wallet_id=dest_wallet.id,
        provider="fireblocks",
        type=TxType.internal_in,
        status=TxStatus.pending,
        amount=payload.amount,
        currency=payload.asset,
        fee_amount=Decimal("0"),
        fee_currency=payload.asset,
        balance_after=dest_balance,
        address_from=wallet.address,
        address_to=dest_wallet.address,
        counterparty_user=current_user.id,
        provider_ref_id=transfer.get("id"),
        group_id=group_id,
    )

    db.add_all([tx_out, tx_in])
    await db.commit()
    await db.refresh(tx_out)

    return WithdrawalResponse(
        transfer_id=transfer.get("id", ""),
        status=transfer.get("status") or transfer.get("state", "pending"),
    )


@router.post("/{wallet_id}/external_transfer", response_model=WithdrawalResponse)
async def external_transfer(
    wallet_id: UUID,
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfer funds from a wallet to an external address or another user."""
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
    # Check if the destination address corresponds to an internal wallet
    result = await db.execute(
        select(Wallet).where(
            Wallet.address == payload.address,
            Wallet.currency == payload.asset,
            Wallet.network == "FIREBLOCKS",
        )
    )
    dest_wallet = result.scalar_one_or_none()

    if dest_wallet:
        sender_balance_data = await get_wallet_balance(wallet.vault_id, payload.asset)
        dest_balance_data = await get_wallet_balance(dest_wallet.vault_id, payload.asset)

        transfer = await transfer_between_vault_accounts(
            wallet.vault_id, dest_wallet.vault_id, payload.asset, payload.amount
        )

        group_id = uuid4()
        amount_dec = Decimal(payload.amount)
        sender_balance = Decimal(sender_balance_data["balance"]) - amount_dec
        dest_balance = Decimal(dest_balance_data["balance"]) + amount_dec

        tx_out = Transaction(
            user_id=current_user.id,
            wallet_id=wallet.id,
            provider="fireblocks",
            type=TxType.internal_out,
            status=TxStatus.pending,
            amount=payload.amount,
            currency=payload.asset,
            fee_amount=Decimal("0"),
            fee_currency=payload.asset,
            balance_after=sender_balance,
            address_from=wallet.address,
            address_to=dest_wallet.address,
            counterparty_user=dest_wallet.user_id,
            provider_ref_id=transfer.get("id"),
            group_id=group_id,
        )
        tx_in = Transaction(
            user_id=dest_wallet.user_id,
            wallet_id=dest_wallet.id,
            provider="fireblocks",
            type=TxType.internal_in,
            status=TxStatus.pending,
            amount=payload.amount,
            currency=payload.asset,
            fee_amount=Decimal("0"),
            fee_currency=payload.asset,
            balance_after=dest_balance,
            address_from=wallet.address,
            address_to=dest_wallet.address,
            counterparty_user=current_user.id,
            provider_ref_id=transfer.get("id"),
            group_id=group_id,
        )
        db.add_all([tx_out, tx_in])
        await db.commit()
        await db.refresh(tx_out)
    else:
        balance_data = await get_wallet_balance(wallet.vault_id, payload.asset)
        transfer = await create_transfer(
            wallet.vault_id, payload.asset, payload.amount, payload.address
        )
        fee = Decimal(str(transfer.get("fee", "0")))
        amount_dec = Decimal(payload.amount)
        balance_after = Decimal(balance_data["balance"]) - amount_dec - fee

        tx = Transaction(
            user_id=current_user.id,
            wallet_id=wallet.id,
            provider="fireblocks",
            type=TxType.crypto_out,
            status=TxStatus.pending,
            amount=payload.amount,
            currency=payload.asset,
            fee_amount=fee,
            fee_currency=payload.asset,
            balance_after=balance_after,
            address_from=wallet.address,
            address_to=payload.address,
            provider_ref_id=transfer.get("id"),
        )
        db.add(tx)
        await db.commit()
        await db.refresh(tx)

    return WithdrawalResponse(
        transfer_id=transfer.get("id", ""),
        status=transfer.get("status") or transfer.get("state", "pending"),
    )


