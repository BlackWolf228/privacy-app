from fireblocks.client import Fireblocks
from fireblocks.client_configuration import ClientConfiguration
from fireblocks.base_path import BasePath
from fireblocks.models.create_vault_account_request import CreateVaultAccountRequest
from app.config import settings
import asyncio


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


async def create_vault_account(name: str, asset: str):
    """Create a Fireblocks vault account and generate a deposit address for ``asset``."""

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

            client.vaults.generate_new_address(vault_account_id, asset).result()
            address_response = client.vaults.get_deposit_address(vault_account_id, asset)
            address = address_response.result().data.address

            return {
                "vault_account_id": vault_account_id,
                "name": name,
                "asset": asset,
                "address": address,
            }

    return await asyncio.to_thread(sync_call)
