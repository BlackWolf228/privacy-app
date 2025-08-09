from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal, InvalidOperation

from fireblocks.client import Fireblocks
from fireblocks.client_configuration import ClientConfiguration
from fireblocks.base_path import BasePath
from fireblocks.models.create_vault_account_request import CreateVaultAccountRequest
from fireblocks.models.transaction_request_amount import TransactionRequestAmount

from app.config import settings


class AssetAlreadyExistsError(Exception):
    """Raised when a vault already contains the requested asset."""


# -------------------
# Helpers
# -------------------

def _as_decimal_str(x, default: str = "0") -> str:
    """
    Normalize various fee/amount shapes to a numeric string.

    Examples accepted:
      - None -> "0"
      - "0.0001" -> "0.0001"
      - 0.0001 -> "0.0001"
      - {"fee": "0.0001"} -> "0.0001"
    """
    try:
        if x is None:
            return default
        if isinstance(x, dict) and "fee" in x:
            return str(Decimal(str(x["fee"])))
        return str(Decimal(str(x)))
    except (InvalidOperation, ValueError, TypeError):
        return default


def _safe_get(obj, *attrs, default=None):
    """Safely extract nested attributes with fallback."""
    cur = obj
    for a in attrs:
        if cur is None:
            return default
        cur = getattr(cur, a, None)
    return cur if cur is not None else default


# -------------------
# Fireblocks client
# -------------------

def get_fireblocks_client() -> Fireblocks:
    config = ClientConfiguration(
        api_key=settings.FIREBLOCKS_API_KEY,
        secret_key=settings.FIREBLOCKS_API_SECRET,
        base_path=BasePath.Sandbox,  # sau BasePath.Production în live
    )
    return Fireblocks(config)


# -------------------
# Address / Asset ops
# -------------------

def generate_new_address(vault_account_id: str, asset_id: str):
    with get_fireblocks_client() as client:
        future = client.vaults.generate_new_address(vault_account_id, asset_id)
        return future.result()


def get_deposit_address(vault_account_id: str, asset_id: str):
    with get_fireblocks_client() as client:
        future = client.vaults.get_deposit_address(vault_account_id, asset_id)
        return future.result().data


async def generate_address_for_vault(vault_account_id: str, asset: str) -> str:
    """Generate a new deposit address for ``asset`` in an existing vault."""

    def sync_call() -> str:
        with get_fireblocks_client() as client:
            client.vaults.generate_new_address(vault_account_id, asset).result()
            address_future = client.vaults.get_deposit_address(vault_account_id, asset)
            return address_future.result().data.address

    return await asyncio.to_thread(sync_call)


async def create_asset_for_vault(vault_account_id: str, asset: str) -> str:
    """Create ``asset`` in an existing vault and return its deposit address.

    Raises:
        AssetAlreadyExistsError: if the asset already exists in this vault.
    """

    def sync_call() -> str:
        with get_fireblocks_client() as client:
            account_future = client.vaults.get_vault_account(vault_account_id)
            account = account_future.result()
            assets = getattr(account.data, "assets", []) or []
            if any(getattr(a, "id", None) == asset for a in assets):
                raise AssetAlreadyExistsError(
                    f"Asset {asset} already exists in vault {vault_account_id}"
                )
            future = client.vaults.create_vault_account_asset(vault_account_id, asset)
            response = future.result()
            return response.data.address

    return await asyncio.to_thread(sync_call)


# -------------------
# Vault ops
# -------------------

async def create_vault_account(name: str):
    """Create a Fireblocks vault account and return its identifier."""

    def sync_call():
        with get_fireblocks_client() as client:
            request = CreateVaultAccountRequest(
                name=name,
                hidden_on_ui=False,
                auto_fuel=False,
            )
            future = client.vaults.create_vault_account(request)
            response = future.result()
            return {
                "vault_account_id": response.data.id,
                "name": name,
            }

    return await asyncio.to_thread(sync_call)


async def get_wallet_balance(vault_account_id: str, asset: str):
    """Return detailed balance information for ``asset`` in ``vault_account_id``."""

    def sync_call():
        with get_fireblocks_client() as client:
            future = client.vaults.get_vault_account_asset(vault_account_id, asset)
            response = future.result()
            data = response.data

            balance = (
                getattr(data, "balance", None)
                or getattr(data, "amount", None)
            )
            currency = getattr(data, "id", asset)
            pending = (
                getattr(data, "pending", None)
                or getattr(data, "pending_balance", None)
                or getattr(data, "pendingBalance", None)
            )
            available = (
                getattr(data, "available", None)
                or getattr(data, "available_balance", None)
                or getattr(data, "availableBalance", None)
            )

            return {
                "balance": balance,
                "asset": currency,
                "pending_balance": pending,
                "available_balance": available,
            }

    return await asyncio.to_thread(sync_call)


# -------------------
# Transfers
# -------------------

async def create_transfer(
    vault_account_id: str,
    asset: str,
    _amount: str,
    destination_address: str,
):
    """Create a transfer from a vault account to an external address."""

    def sync_call() -> dict:
        with get_fireblocks_client() as client:
            tx_request = {
                "assetId": asset,
                "source": {"type": "VAULT_ACCOUNT", "id": vault_account_id},
                "destination": {
                    "type": "ONE_TIME_ADDRESS",
                    "oneTimeAddress": {"address": destination_address},
                },
                # SDK-ul așteaptă TransactionRequestAmount aici
                "amount": TransactionRequestAmount(_amount),
            }
            future = client.transactions.create_transaction(
                transaction_request=tx_request
            )
            response = future.result()
            data = getattr(response, "data", response)

            # Normalizează fee
            fee_info = _safe_get(data, "fee_info") or _safe_get(data, "feeInfo")
            raw_fee = getattr(fee_info, "fee", None) if fee_info else getattr(data, "fee", None)
            fee = _as_decimal_str(raw_fee, "0")

            return {
                "id": getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "state": getattr(data, "state", None),
                "fee": fee,  # întotdeauna string numeric
            }

    return await asyncio.to_thread(sync_call)


async def transfer_between_vault_accounts(
    source_vault_id: str,
    destination_vault_id: str,
    asset: str,
    _amount: str,
):
    """Transfer assets between two Fireblocks vault accounts."""

    def sync_call() -> dict:
        with get_fireblocks_client() as client:
            tx_request = {
                "assetId": asset,
                "source": {"type": "VAULT_ACCOUNT", "id": source_vault_id},
                "destination": {"type": "VAULT_ACCOUNT", "id": destination_vault_id},
                # SDK-ul așteaptă TransactionRequestAmount aici
                "amount": TransactionRequestAmount(_amount),
            }
            idempotency_key = uuid.uuid4().hex
            future = client.transactions.create_transaction(
                idempotency_key=idempotency_key,
                transaction_request=tx_request,
            )
            response = future.result()
            data = getattr(response, "data", response)
            return {
                "id": getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "state": getattr(data, "state", None),
            }

    return await asyncio.to_thread(sync_call)
