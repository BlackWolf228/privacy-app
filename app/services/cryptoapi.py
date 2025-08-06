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
    """Create a wallet using CryptoAPI Wallet as a Service.

    Args:
        currency: Currency code (e.g., 'BTC').
        network: Network/chain where the wallet will live.

    Returns:
        A dictionary with ``wallet_id`` and ``address``.

    Raises:
        error.HTTPError: If the API returns an error status code.
        error.URLError: If a network error occurs after retries.
    """
    if not API_KEY:
        raise CryptoAPIError("CRYPTO_API_KEY is not set")
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = json.dumps({"currency": currency, "network": network}).encode()

    req = request.Request(
        f"{API_BASE_URL}/wallets",
        data=payload,
        headers=headers,
        method="POST",
    )

    last_exc = None
    for _ in range(3):
        try:
            def do_request():
                with request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    return {
                        "wallet_id": data.get("wallet_id"),
                        "address": data.get("address"),
                    }

            return await asyncio.to_thread(do_request)
        except error.HTTPError as exc:
            # Client errors should not be retried
            raise exc
        except error.URLError as exc:
            last_exc = exc
            continue
    raise last_exc
