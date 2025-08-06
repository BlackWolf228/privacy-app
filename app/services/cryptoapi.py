import json
import asyncio
from typing import Dict

from urllib import request, error

from app.config import settings

API_BASE_URL = settings.CRYPTO_API_BASE_URL
API_KEY = settings.CRYPTO_API_KEY

SUPPORTED_NETWORKS = {
    "BTC": ["BITCOIN"],
    "ETH": ["ETHEREUM"],
    "USDT": ["TRON", "TONCOIN", "NEAR", "POLYGON", "ETHEREUM", "ARBITRUM"],
    "TRX": ["TRON"],
    "ARB": ["ARBITRUM"],
    "LTC": ["LITECOIN"],
    "USDC": ["SOLANA", "NEAR", "POLYGON", "ETHEREUM", "BSC"],
    "BNB": ["BSC"],
    "DOGE": ["DOGECOIN"],
    "POL": ["POLYGON"],
    "SOL": ["SOLANA"],
    "XLM": ["STELLAR"],
    "XRP": ["RIPPLE"],
}

class CryptoAPIError(Exception):
    """Generic error raised when the CryptoAPI request fails."""

async def create_wallet(currency: str, network: str) -> Dict[str, str]:
    """Create an HD wallet using CryptoAPI Wallet as a Service.

    Args:
        currency: Currency code (e.g., ``"BTC"``).
        network: Network/chain where the wallet will live (e.g., ``"BITCOIN"``).

    Returns:
        A dictionary with ``wallet_id`` and ``xpub`` returned by the API.

    Raises:
        CryptoAPIError: If the API returns an error status code.
        error.URLError: If a network error occurs after retries.
    """
    if not API_KEY:
        raise CryptoAPIError("CRYPTO_API_KEY is not set")
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    # Endpoint requires currency and network as path params.
    req = request.Request(
        f"{API_BASE_URL}/wallet-as-a-service/wallets/hd/{currency}/{network}",
        data=json.dumps({"context": "create-wallet"}).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    last_exc = None
    for _ in range(3):
        try:
            def do_request():
                with request.urlopen(req, timeout=10) as resp:
                    raw = json.loads(resp.read().decode())
                    item = raw.get("data", {}).get("item", raw)
                    return {
                        "wallet_id": item.get("walletId") or item.get("wallet_id"),
                        "xpub": item.get("xpub"),
                    }

            return await asyncio.to_thread(do_request)
        except error.HTTPError as exc:
            # surface API error details for easier debugging
            body = exc.read().decode()
            try:
                detail = json.loads(body)
            except json.JSONDecodeError:
                detail = body or exc.reason
            raise CryptoAPIError(f"HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            last_exc = exc
            continue
    raise last_exc
