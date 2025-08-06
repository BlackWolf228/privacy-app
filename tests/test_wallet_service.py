import asyncio
import io
import json
from pathlib import Path
import sys
from urllib import request, error

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
        assert req.full_url.endswith("/wallets/BTC/BITCOIN")
        return DummyResponse({"wallet_id": "w1", "address": "addr"})

    monkeypatch.setattr(cryptoapi, "API_KEY", "test-key")
    monkeypatch.setattr(request, "urlopen", fake_urlopen)

    async def call():
        result = await cryptoapi.create_wallet("BTC", "BITCOIN")
        assert result == {"wallet_id": "w1", "address": "addr"}

    asyncio.run(call())


def test_create_wallet_http_error(monkeypatch):
    class DummyHTTPError(error.HTTPError):
        def __init__(self):
            fp = io.BytesIO(b'{"message": "Invalid"}')
            super().__init__('url', 400, 'Bad Request', {}, fp)

    def fake_urlopen(req, timeout=10):
        raise DummyHTTPError()

    monkeypatch.setattr(cryptoapi, 'API_KEY', 'test-key')
    monkeypatch.setattr(request, 'urlopen', fake_urlopen)

    async def call():
        with pytest.raises(cryptoapi.CryptoAPIError) as exc_info:
            await cryptoapi.create_wallet('BTC', 'BITCOIN')
        assert 'Invalid' in str(exc_info.value)

    asyncio.run(call())
