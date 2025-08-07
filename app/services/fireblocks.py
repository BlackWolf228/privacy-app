from fireblocks.client import Fireblocks
from fireblocks.client_configuration import ClientConfiguration
from fireblocks.base_path import BasePath
from fireblocks.models.create_vault_account_request import CreateVaultAccountRequest
from app.config import settings
import asyncio


class AssetAlreadyExistsError(Exception):
    """Raised when a vault already contains the requested asset."""


def get_fireblocks_client() -> Fireblocks:
    config = ClientConfiguration(
        api_key=settings.FIREBLOCKS_API_KEY,
        secret_key=settings.FIREBLOCKS_API_SECRET,
        base_path=BasePath.Sandbox  # sau BasePath.Production dacă folosești live
    )
    return Fireblocks(config)


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

    If the asset already exists for the specified vault, an
    :class:`AssetAlreadyExistsError` is raised instead of generating another
    address.
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
            vault_account_id = response.data.id

            return {
                "vault_account_id": vault_account_id,
                "name": name,
            }

    return await asyncio.to_thread(sync_call)


async def get_wallet_balance(vault_account_id: str, asset: str):
    """Return the balance of ``asset`` for a specific vault.

    This wrapper relies on Fireblocks' :func:`get_vault_account_asset` API
    so the balance reflects only the supplied ``vault_account_id``.  The
    previously used :func:`get_vault_balance_by_asset` aggregates amounts
    across all vaults in the workspace and is therefore unsuitable when a
    per-vault balance is needed.
    """

    def sync_call():
        with get_fireblocks_client() as client:
            # ``get_vault_account_asset`` returns the balance for a specific
            # asset within the given vault.
            future = client.vaults.get_vault_account_asset(vault_account_id, asset)
            response = future.result()
            data = response.data
            amount = getattr(data, "balance", None) or getattr(data, "amount", None)
            currency = getattr(data, "id", asset)
            return {"amount": amount, "currency": currency}

    return await asyncio.to_thread(sync_call)


async def create_transfer(
    vault_account_id: str, asset: str, amount: str, destination_address: str
):
    """Create a transfer from a vault account to an external address.

    Parameters
    ----------
    vault_account_id:
        The identifier of the source vault account.
    asset:
        The asset symbol to transfer.
    amount:
        The amount to be transferred as a string to avoid precision issues.
    destination_address:
        The blockchain address where the funds should be sent.

    Returns
    -------
    dict
        A dictionary containing the transaction ``id`` and ``status`` as
        reported by Fireblocks.  The exact fields returned by the SDK may vary,
        so unknown attributes are safely accessed using :func:`getattr`.
    """

    def sync_call() -> dict:
        with get_fireblocks_client() as client:
            tx_request = {
                "assetId": asset,
                "source": {"type": "VAULT_ACCOUNT", "id": vault_account_id},
                "destination": {
                    "type": "ONE_TIME_ADDRESS",
                    "oneTimeAddress": {"address": destination_address},
                },
                "amount": amount,
            }
            future = client.transactions.create_transaction(tx_request)
            response = future.result()
            data = getattr(response, "data", response)
            return {
                "id": getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "state": getattr(data, "state", None),
            }

    return await asyncio.to_thread(sync_call)


async def transfer_between_vault_accounts(
    source_vault_id: str, destination_vault_id: str, asset: str, amount: str
):
    """Transfer assets between two Fireblocks vault accounts.

    This helper wraps the SDK's ``transfer_between_vault_accounts`` call and
    returns a small dictionary with the resulting transaction ``id`` and
    ``status``/``state`` fields.  The Fireblocks SDK returns different shapes
    depending on version so attributes are accessed defensively via
    :func:`getattr`.

    Parameters
    ----------
    source_vault_id:
        Identifier of the vault from which funds will be debited.
    destination_vault_id:
        Identifier of the vault that will receive the funds.
    asset:
        Asset symbol to transfer.
    amount:
        Amount of ``asset`` to transfer as a string.
    """

    def sync_call() -> dict:
        with get_fireblocks_client() as client:
            tx_request = {
                "assetId": asset,
                "source": {"type": "VAULT_ACCOUNT", "id": source_vault_id},
                "destination": {
                    "type": "VAULT_ACCOUNT",
                    "id": destination_vault_id,
                },
                "amount": amount,
            }
            future = client.transfer_between_vault_accounts(tx_request)
            response = future.result()
            data = getattr(response, "data", response)
            return {
                "id": getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "state": getattr(data, "state", None),
            }

    return await asyncio.to_thread(sync_call)
