import os
import json
import uuid
import asyncio
from typing import Dict, Any
from urllib import request, error

# Circle API configuration
API_BASE_URL = os.getenv("CIRCLE_API_BASE_URL", "https://api.circle.com/v1")
API_KEY = os.getenv("CIRCLE_API_KEY", "")

# Networks supported for USDC wallets
CIRCLE_NETWORK_MAP = {
    "ETHEREUM": "ETH",
    "POLYGON": "MATIC",
    "SOLANA": "SOL",
}

SUPPORTED_NETWORKS = {"USDC": list(CIRCLE_NETWORK_MAP.keys())}

class CircleAPIError(Exception):
    """Raised when the Circle API request fails."""

async def _do_request(url: str, method: str = "GET", data: Any = None) -> Dict[str, Any]:
    """Internal helper to perform HTTP requests to Circle API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    req = request.Request(
        f"{API_BASE_URL}{url}",
        data=data,
        headers=headers,
        method=method,
    )
    def do_request():
        with request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    return await asyncio.to_thread(do_request)

async def create_wallet(currency: str, network: str) -> Dict[str, str]:
    """Create a custodial wallet for the given network."""
    payload = json.dumps(
        {
            "idempotencyKey": str(uuid.uuid4()),
            "type": "custodial",
            "blockchain": CIRCLE_NETWORK_MAP[network],
        }
    ).encode()
    data = await _do_request("/wallets", method="POST", data=payload)
    wallet = data.get("data", {})
    return {
        "wallet_id": wallet.get("walletId"),
        "address": wallet.get("address"),
    }

async def get_wallet_balance(wallet_id: str) -> Dict[str, Any]:
    """Retrieve balances for a wallet."""
    data = await _do_request(f"/wallets/{wallet_id}/balances")
    balances = data.get("data", {}).get("tokenBalances", [])
    for item in balances:
        if item.get("token", {}).get("symbol") == "USDC":
            return {
                "amount": item.get("amount"),
                "currency": "USDC",
            }
    return {"amount": "0", "currency": "USDC"}

async def create_transfer(wallet_id: str, address: str, amount: str, network: str) -> Dict[str, Any]:
    """Initiate a withdrawal from a wallet to a blockchain address."""
    payload = json.dumps(
        {
            "idempotencyKey": str(uuid.uuid4()),
            "source": {"type": "wallet", "id": wallet_id},
            "destination": {
                "type": "blockchain",
                "address": address,
                "chain": CIRCLE_NETWORK_MAP[network],
            },
            "amount": {"amount": amount, "currency": "USDC"},
        }
    ).encode()
    data = await _do_request("/transfers", method="POST", data=payload)
    return data.get("data", {})
