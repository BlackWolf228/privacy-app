import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
import pytest

from app.services import fireblocks


class DummySDK:
    def __init__(self, *args, **kwargs):
        pass

    def create_vault_account(self, name):
        assert name == "alice"
        return {"id": "1", "name": name}

    def get_vault_account(self, vault_account_id):
        assert vault_account_id == "1"
        return {"assets": [{"id": "BTC", "total": "0.5"}]}

    def create_transaction(self, **kwargs):
        assert kwargs["assetId"] == "BTC"
        assert kwargs["amount"] == "0.1"
        return {"id": "tx1"}


def test_create_vault_account(monkeypatch):
    monkeypatch.setattr(fireblocks, "FireblocksSDK", DummySDK)
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_KEY", "key")
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_SECRET", "secret")

    result = asyncio.run(fireblocks.create_vault_account("alice"))
    assert result == {"vault_account_id": "1", "name": "alice"}


def test_get_wallet_balance(monkeypatch):
    monkeypatch.setattr(fireblocks, "FireblocksSDK", DummySDK)
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_KEY", "key")
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_SECRET", "secret")

    result = asyncio.run(fireblocks.get_wallet_balance("1", "BTC"))
    assert result == {"amount": "0.5", "currency": "BTC"}


def test_create_transfer(monkeypatch):
    class TransferSDK(DummySDK):
        def create_transaction(self, **kwargs):
            assert kwargs["source"] == {"type": "VAULT_ACCOUNT", "id": "1"}
            assert kwargs["destination"]["oneTimeAddress"]["address"] == "dest"
            return {"id": "tx1"}

    monkeypatch.setattr(fireblocks, "FireblocksSDK", TransferSDK)
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_KEY", "key")
    monkeypatch.setattr(fireblocks.settings, "FIREBLOCKS_API_SECRET", "secret")

    result = asyncio.run(fireblocks.create_transfer("1", "BTC", "0.1", "dest"))
    assert result == {"id": "tx1"}

