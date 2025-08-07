import asyncio
import hmac
import hashlib
import json
import time
from typing import Any, Dict

import requests

from app.config import settings

API_BASE_URL = settings.FIREBLOCKS_API_BASE_URL
API_KEY = settings.FIREBLOCKS_API_KEY
API_SECRET = settings.FIREBLOCKS_API_SECRET


class FireblocksAPIError(Exception):
    """Raised when a Fireblocks API request fails."""


def sign_request(method: str, path: str, body: str = "") -> Dict[str, str]:
    """Generate headers for a Fireblocks API request using HMAC SHA-256."""
    if not API_KEY or not API_SECRET:
        raise FireblocksAPIError("Fireblocks API credentials are not set")
    nonce = str(int(time.time() * 1000))
    message = f"{nonce}{method.upper()}{path}{body}"
    signature = hmac.new(API_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {
        "X-API-Key": API_KEY,
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


async def _request(method: str, path: str, body: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = json.dumps(body) if body else ""
    headers = sign_request(method, path, payload)
    url = f"{API_BASE_URL}{path}"

    def do_request():
        resp = requests.request(method, url, headers=headers, data=payload or None)
        try:
            resp.raise_for_status()
        except requests.exceptions.HTTPError as exc:  # pragma: no cover - network errors
            raise FireblocksAPIError(resp.text) from exc
        return resp.json()

    return await asyncio.to_thread(do_request)


async def create_vault_account(name: str) -> Dict[str, str]:
    """Create a new Fireblocks vault account."""
    data = await _request("POST", "/v1/vault/accounts", {"name": name})
    account = data.get("data", {})
    return {"vault_account_id": account.get("id"), "name": account.get("name")}


async def get_wallet_balance(vault_account_id: str, asset: str) -> Dict[str, str]:
    """Retrieve the balance for a specific asset in a vault account."""
    data = await _request("GET", f"/v1/vault/accounts/{vault_account_id}")
    for item in data.get("data", {}).get("assets", []):
        if item.get("id") == asset:
            return {"amount": item.get("total"), "currency": asset}
    return {"amount": "0", "currency": asset}


async def create_transfer(
    vault_account_id: str, asset: str, amount: str, address: str
) -> Dict[str, Any]:
    """Initiate a transfer from a vault account to an external address."""
    body = {
        "assetId": asset,
        "source": {"type": "VAULT_ACCOUNT", "id": vault_account_id},
        "destination": {
            "type": "ONE_TIME_ADDRESS",
            "oneTimeAddress": {"address": address},
        },
        "amount": amount,
    }
    data = await _request("POST", "/v1/transfer", body)
    return data.get("data", {})
