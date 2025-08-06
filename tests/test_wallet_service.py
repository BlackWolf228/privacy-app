import asyncio
import json
from urllib import error, request

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest

from app.services.cryptoapi import create_wallet


class DummyResponse:
    def __init__(self, data):
        self._data = json.dumps(data).encode()

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_create_wallet_success(monkeypatch):
    def mock_urlopen(req, timeout=10):
        return DummyResponse({"wallet_id": "w123", "address": "addr123"})

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    async def call():
        data = await create_wallet("BTC", "BITCOIN")
        assert data["wallet_id"] == "w123"
        assert data["address"] == "addr123"

    asyncio.run(call())


def test_create_wallet_invalid_key(monkeypatch):
    def mock_urlopen(req, timeout=10):
        raise error.HTTPError(req.full_url, 401, "unauthorized", hdrs=None, fp=None)

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    async def call():
        with pytest.raises(error.HTTPError):
            await create_wallet("BTC", "BITCOIN")

    asyncio.run(call())


def test_create_wallet_connection_error(monkeypatch):
    def mock_urlopen(req, timeout=10):
        raise error.URLError("boom")

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    async def call():
        with pytest.raises(error.URLError):
            await create_wallet("BTC", "BITCOIN")

    asyncio.run(call())
