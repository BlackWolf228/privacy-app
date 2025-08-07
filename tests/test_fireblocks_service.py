import asyncio
from types import SimpleNamespace
import types
import sys
from pathlib import Path

import pytest

# Ensure repository root on path for "app" package imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub out the third-party Fireblocks package used by the service so that the
# module can be imported without the real dependency being installed.
fireblocks_stub = types.ModuleType("fireblocks")
client_mod = types.ModuleType("fireblocks.client")
client_config_mod = types.ModuleType("fireblocks.client_configuration")
base_path_mod = types.ModuleType("fireblocks.base_path")
models_mod = types.ModuleType("fireblocks.models")
models_request_mod = types.ModuleType("fireblocks.models.create_vault_account_request")

class Fireblocks:  # pragma: no cover - simple placeholder
    pass

class ClientConfiguration:  # pragma: no cover - simple placeholder
    def __init__(self, *args, **kwargs):
        pass

class BasePath:  # pragma: no cover - simple placeholder
    Sandbox = object()

class CreateVaultAccountRequest:  # pragma: no cover - simple placeholder
    def __init__(self, *args, **kwargs):
        pass

client_mod.Fireblocks = Fireblocks
client_config_mod.ClientConfiguration = ClientConfiguration
base_path_mod.BasePath = BasePath
models_request_mod.CreateVaultAccountRequest = CreateVaultAccountRequest

sys.modules.update(
    {
        "fireblocks": fireblocks_stub,
        "fireblocks.client": client_mod,
        "fireblocks.client_configuration": client_config_mod,
        "fireblocks.base_path": base_path_mod,
        "fireblocks.models": models_mod,
        "fireblocks.models.create_vault_account_request": models_request_mod,
    }
)

from app.services import fireblocks as fb


def test_get_wallet_balance_uses_vault_account_asset(monkeypatch):
    """Ensure ``get_wallet_balance`` queries a specific vault asset."""

    class DummyFuture:
        def result(self):
            # mimic Fireblocks response structure
            return SimpleNamespace(
                data=SimpleNamespace(
                    balance="10",
                    id="BTC_TEST",
                    pending="1",
                    available="9",
                )
            )

    class DummyVaults:
        def __init__(self):
            self.calls = []

        def get_vault_account_asset(self, vault_id, asset_id):
            self.calls.append((vault_id, asset_id))
            return DummyFuture()

    class DummyClient:
        def __init__(self):
            self.vaults = DummyVaults()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    dummy_client = DummyClient()
    monkeypatch.setattr(fb, "get_fireblocks_client", lambda: dummy_client)

    result = asyncio.run(fb.get_wallet_balance("V1", "BTC_TEST"))

    assert dummy_client.vaults.calls == [("V1", "BTC_TEST")]
    assert result == {
        "balance": "10",
        "asset": "BTC_TEST",
        "pending_balance": "1",
        "available_balance": "9",
    }


def test_create_transfer_creates_transaction(monkeypatch):
    """Ensure ``create_transfer`` sends a transaction request."""

    class DummyFuture:
        def result(self):
            return SimpleNamespace(data=SimpleNamespace(id="T1", status="COMPLETED"))

    class DummyTransactions:
        def __init__(self):
            self.calls = []

        def create_transaction(self, *, transaction_request):
            self.calls.append(transaction_request)
            return DummyFuture()

    class DummyClient:
        def __init__(self):
            self.transactions = DummyTransactions()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    dummy_client = DummyClient()
    monkeypatch.setattr(fb, "get_fireblocks_client", lambda: dummy_client)

    result = asyncio.run(
        fb.create_transfer("V1", "BTC_TEST", "0.1", "ADDR")
    )

    assert dummy_client.transactions.calls == [
        {
            "assetId": "BTC_TEST",
            "source": {"type": "VAULT_ACCOUNT", "id": "V1"},
            "destination": {
                "type": "ONE_TIME_ADDRESS",
                "oneTimeAddress": {"address": "ADDR"},
            },
            "amount": "0.1",
        }
    ]
    assert result["id"] == "T1"
    assert result["status"] == "COMPLETED"


def test_transfer_between_vault_accounts(monkeypatch):
    """Ensure ``transfer_between_vault_accounts`` issues a vault transfer."""

    class DummyFuture:
        def result(self):
            return SimpleNamespace(data=SimpleNamespace(id="T2", status="COMPLETED"))

    class DummyTransactions:
        def __init__(self):
            self.calls = []

        def create_transaction(self, *, idempotency_key, transaction_request):
            self.calls.append((idempotency_key, transaction_request))
            return DummyFuture()

    class DummyClient:
        def __init__(self):
            self.transactions = DummyTransactions()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    dummy_client = DummyClient()
    monkeypatch.setattr(fb, "get_fireblocks_client", lambda: dummy_client)

    result = asyncio.run(
        fb.transfer_between_vault_accounts("V1", "V2", "BTC_TEST", "0.1")
    )

    assert len(dummy_client.transactions.calls) == 1
    idempotency_key, request = dummy_client.transactions.calls[0]
    assert isinstance(idempotency_key, str) and len(idempotency_key) == 32
    assert request == {
        "assetId": "BTC_TEST",
        "source": {"type": "VAULT_ACCOUNT", "id": "V1"},
        "destination": {"type": "VAULT_ACCOUNT", "id": "V2"},
        "amount": "0.1",
    }
    assert result["id"] == "T2"
    assert result["status"] == "COMPLETED"
