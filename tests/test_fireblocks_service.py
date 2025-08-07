import sys
from pathlib import Path
import asyncio
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub minimal fireblocks SDK modules so app.services.fireblocks can import
fireblocks_stub = types.ModuleType("fireblocks")
client_mod = types.ModuleType("fireblocks.client")
client_mod.Fireblocks = object
client_conf_mod = types.ModuleType("fireblocks.client_configuration")
client_conf_mod.ClientConfiguration = object
base_path_mod = types.ModuleType("fireblocks.base_path")
base_path_mod.BasePath = types.SimpleNamespace(Sandbox=None)
req_mod = types.ModuleType("fireblocks.models.create_vault_account_request")


class DummyRequest:
    def __init__(self, name, hidden_on_ui=False, auto_fuel=False):
        self.name = name


req_mod.CreateVaultAccountRequest = DummyRequest

sys.modules["fireblocks"] = fireblocks_stub
sys.modules["fireblocks.client"] = client_mod
sys.modules["fireblocks.client_configuration"] = client_conf_mod
sys.modules["fireblocks.base_path"] = base_path_mod
sys.modules["fireblocks.models.create_vault_account_request"] = req_mod

from app.services import fireblocks


class DummyFuture:
    def __init__(self, value):
        self._value = value

    def result(self):
        return self._value


class DummyVaults:
    def __init__(self):
        self.generate_called = False
        self.get_called = False

    def create_vault_account(self, request):
        data = type("Resp", (), {"data": type("Data", (), {"id": "1", "name": request.name})()})()
        return DummyFuture(data)

    def generate_new_address(self, vault_account_id, asset):
        self.generate_called = True
        return DummyFuture(None)

    def get_deposit_address(self, vault_account_id, asset):
        self.get_called = True
        data = type("Resp", (), {"data": type("Data", (), {"address": "ADDR123"})()})()
        return DummyFuture(data)


class DummyClient:
    def __init__(self):
        self.vaults = DummyVaults()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def test_create_vault_account(monkeypatch):
    dummy_client = DummyClient()
    monkeypatch.setattr(fireblocks, "get_fireblocks_client", lambda: dummy_client)
    result = asyncio.run(fireblocks.create_vault_account("alice"))
    assert result == {"vault_account_id": "1", "name": "alice"}
    assert dummy_client.vaults.generate_called is False
    assert dummy_client.vaults.get_called is False

