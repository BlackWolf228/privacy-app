import asyncio

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.services import cryptoapi


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def read(self):
        return json.dumps(self._data).encode()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def test_create_wallet_uses_api_key(monkeypatch):
    def fake_urlopen(req, timeout=10):
        assert req.headers["X-api-key"] == "test-key"
        return DummyResponse({"wallet_id": "w1", "address": "addr"})

    monkeypatch.setattr(cryptoapi, "API_KEY", "test-key")
    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    async def call():
        result = await cryptoapi.create_wallet("BTC", "BITCOIN")
        assert result == {"wallet_id": "w1", "address": "addr"}

    asyncio.run(call())
