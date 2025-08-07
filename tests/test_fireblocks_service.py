import asyncio
import json
import hmac
import hashlib
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pytest
requests = pytest.importorskip("requests")

from app.services import fireblocks


def test_sign_request_hmac(monkeypatch):
    monkeypatch.setattr(fireblocks, "API_KEY", "key")
    monkeypatch.setattr(fireblocks, "API_SECRET", "secret")
    monkeypatch.setattr(fireblocks.time, "time", lambda: 1700000000.0)
    headers = fireblocks.sign_request("GET", "/v1/test", "")
    assert headers["X-API-Key"] == "key"
    assert headers["X-Nonce"] == "1700000000000"
    expected = hmac.new(b"secret", b"1700000000000GET/v1/test", hashlib.sha256).hexdigest()
    assert headers["X-Signature"] == expected


def test_create_vault_account(monkeypatch):
    monkeypatch.setattr(fireblocks, "API_KEY", "key")
    monkeypatch.setattr(fireblocks, "API_SECRET", "secret")
    monkeypatch.setattr(fireblocks, "API_BASE_URL", "https://api")
    monkeypatch.setattr(fireblocks.time, "time", lambda: 1700000000.0)

    def fake_request(method, url, headers=None, data=None):
        assert method == "POST"
        assert url == "https://api/v1/vault/accounts"
        payload = json.dumps({"name": "alice"})
        assert data == payload
        expected_msg = "1700000000000POST/v1/vault/accounts" + payload
        expected_sig = hmac.new(b"secret", expected_msg.encode(), hashlib.sha256).hexdigest()
        assert headers["X-Signature"] == expected_sig
        assert headers["X-API-Key"] == "key"

        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": {"id": "1", "name": "alice"}}

        return Resp()

    monkeypatch.setattr(requests, "request", fake_request)

    async def call():
        result = await fireblocks.create_vault_account("alice")
        assert result == {"vault_account_id": "1", "name": "alice"}

    asyncio.run(call())
