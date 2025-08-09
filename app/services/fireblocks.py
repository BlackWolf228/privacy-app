from fireblocks.client import Fireblocks
from fireblocks.client_configuration import ClientConfiguration
from fireblocks.base_path import BasePath
from fireblocks.models.create_vault_account_request import CreateVaultAccountRequest
from fireblocks.models.transaction_request_amount import TransactionRequestAmount
from app.config import settings
import asyncio
import uuid


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
    """Return detailed balance information for ``asset`` in ``vault_account_id``.

    The Fireblocks SDK returns slightly different shapes depending on
    version.  All attributes are therefore accessed defensively using
    :func:`getattr` so that missing fields simply yield ``None`` instead of
    raising an exception.
    """

    def sync_call():
        with get_fireblocks_client() as client:
            future = client.vaults.get_vault_account_asset(vault_account_id, asset)
            response = future.result()
            data = response.data
            balance = getattr(data, "balance", None) or getattr(data, "amount", None)
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


async def create_transfer(
    vault_account_id: str, asset: str, _amount: str, destination_address: str
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
                # Fireblocks expects the amount as a structured
                # ``TransactionRequestAmount`` object rather than a raw
                # string value.
                "amount": TransactionRequestAmount(amount=_amount),
            }
            # The Fireblocks SDK expects keyword arguments for optional
            # parameters.  Passing the transaction request positionally causes
            # it to be interpreted as the ``x_end_user_wallet_id`` value which
            # then fails validation.  Use an explicit keyword argument so the
            # request is parsed correctly.
            future = client.transactions.create_transaction(
                transaction_request=tx_request
            )
            response = future.result()
            data = getattr(response, "data", response)
            fee_info = getattr(data, "fee_info", None) or getattr(data, "feeInfo", None)
            fee = getattr(fee_info, "fee", None) if fee_info else getattr(data, "fee", None)
            return {
                "id": getattr(data, "id", None),
                "status": getattr(data, "status", None),
                "state": getattr(data, "state", None),
                "fee": fee,
            }

    return await asyncio.to_thread(sync_call)


async def transfer_between_vault_accounts(
    source_vault_id: str, destination_vault_id: str, asset: str, _amount: str
):
    """Transfer assets between two Fireblocks vault accounts.

    This helper creates a transaction between two vault accounts using the
    standard Fireblocks ``create_transaction`` API and returns a small
    dictionary with the resulting transaction ``id`` and ``status``/``state``
    fields.  The Fireblocks SDK returns different shapes depending on
    version so attributes are accessed defensively via :func:`getattr`.

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
                # The amount is provided as a ``TransactionRequestAmount``
                # instance rather than a plain string.
                "amount": TransactionRequestAmount(amount=_amount),
            }
            idempotency_key = uuid.uuid4().hex
            # Similar to the external transfer above, the SDK validates
            # positional arguments against ``x_end_user_wallet_id`` and
            # ``idempotency_key``.  When the transaction request is supplied as
            # a positional argument it is treated as the idempotency key,
            # resulting in a Pydantic validation error.  Supplying keyword
            # arguments ensures correct parameter mapping.
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
