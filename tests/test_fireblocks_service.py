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
            return SimpleNamespace(data=SimpleNamespace(balance="10", id="BTC_TEST"))

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
    assert result == {"amount": "10", "currency": "BTC_TEST"}
