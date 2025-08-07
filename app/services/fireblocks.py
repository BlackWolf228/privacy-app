"""Helpers for interacting with the Fireblocks API.

This module now relies on the official `fireblocks-sdk` package instead of
manually crafting HTTP requests.  The SDK performs the required request
signing and exposes convenient Python methods.  We keep an asynchronous
interface by delegating the blocking SDK calls to a worker thread.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fireblocks_sdk import FireblocksSDK

from app.config import settings


class FireblocksAPIError(Exception):
    """Raised when Fireblocks API credentials are missing."""


def _get_client() -> FireblocksSDK:
    """Create a Fireblocks SDK client from the application settings."""
    if not settings.FIREBLOCKS_API_KEY or not settings.FIREBLOCKS_API_SECRET:
        raise FireblocksAPIError("Fireblocks API credentials are not set")
    return FireblocksSDK(
        settings.FIREBLOCKS_API_SECRET,
        settings.FIREBLOCKS_API_KEY,
        api_base_url=settings.FIREBLOCKS_API_BASE_URL,
    )


async def create_vault_account(name: str, asset: str = "BTC_TEST") -> Dict[str, str]:
    """Create a new Fireblocks vault account and generate a deposit address.

    Parameters
    ----------
    name:
        The label of the vault account to create.
    asset:
        The Fireblocks asset ID to generate a deposit address for.  Tests
        currently exercise ``BTC_TEST`` and ``ETH_TEST5``.
    """

    client = _get_client()

    def create_call() -> Dict[str, Any]:
        return client.create_vault_account(name)

    account = await asyncio.to_thread(create_call)
    vault_id = account.get("id")

    def address_call() -> Dict[str, Any]:
        return client.generate_deposit_address(vault_id, asset)

    addr = await asyncio.to_thread(address_call)
    return {
        "vault_account_id": vault_id,
        "name": account.get("name"),
        "asset": asset,
        "address": addr.get("address"),
    }


async def get_wallet_balance(vault_account_id: str, asset: str) -> Dict[str, str]:
    """Retrieve the balance for a specific asset in a vault account."""

    client = _get_client()

    def call() -> Dict[str, Any]:
        return client.get_vault_account(vault_account_id)

    data = await asyncio.to_thread(call)
    for item in data.get("assets", []):
        if item.get("id") == asset:
            return {"amount": item.get("total"), "currency": asset}
    return {"amount": "0", "currency": asset}


async def create_transfer(
    vault_account_id: str, asset: str, amount: str, address: str
) -> Dict[str, Any]:
    """Initiate a transfer from a vault account to an external address."""

    client = _get_client()

    def call() -> Dict[str, Any]:
        return client.create_transaction(
            assetId=asset,
            amount=amount,
            source={"type": "VAULT_ACCOUNT", "id": vault_account_id},
            destination={
                "type": "ONE_TIME_ADDRESS",
                "oneTimeAddress": {"address": address},
            },
        )

    return await asyncio.to_thread(call)

