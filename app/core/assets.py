from dataclasses import dataclass
from typing import Callable, Optional
import re
try:
    from eth_utils import is_checksum_address as eth_is_checksum
except Exception:
    eth_is_checksum = None

@dataclass(frozen=True)
class AssetMeta:
    symbol: str
    network: str
    decimals: int
    native: bool
    address_validator: Optional[Callable[[str], bool]] = None

_re_btc_main = re.compile(r"^(bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{14,64}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$")
_re_btc_test = re.compile(r"^(tb1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{14,64}|[mn2][a-km-zA-HJ-NP-Z1-9]{25,34})$")
_re_eth = re.compile(r"^0x[a-fA-F0-9]{40}$")
_re_tron = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")

def is_btc_main(addr: str) -> bool:
    return bool(_re_btc_main.match(addr or ""))

def is_btc_test(addr: str) -> bool:
    return bool(_re_btc_test.match(addr or ""))

def is_eth(addr: str) -> bool:
    if not _re_eth.match(addr or ""):
        return False
    if eth_is_checksum:
        if addr == addr.lower() or addr == addr.upper() or eth_is_checksum(addr):
            return True
        return False
    return True

def is_tron(addr: str) -> bool:
    return bool(_re_tron.match(addr or ""))

ASSETS: dict[str, AssetMeta] = {
    "BTC":       AssetMeta("BTC",       "BTC",   8,  True,  is_btc_main),
    "BTC_TEST":  AssetMeta("BTC_TEST",  "BTC",   8,  True,  is_btc_test),
    "ETH":       AssetMeta("ETH",       "ETH",  18,  True,  is_eth),
    "ETH_TEST":  AssetMeta("ETH_TEST",  "ETH",  18,  True,  is_eth),
    "TRX":       AssetMeta("TRX",       "TRON",  6,  True,  is_tron),
    "USDT_ERC20":AssetMeta("USDT",      "ETH",   6,  False, is_eth),
    "USDT_TRC20":AssetMeta("USDT",      "TRON",  6,  False, is_tron),
}

def get_asset(symbol: str) -> AssetMeta:
    meta = ASSETS.get(symbol)
    if not meta:
        raise ValueError(f"Unsupported asset: {symbol}")
    return meta

def validate_destination(asset_symbol: str, address: str) -> bool:
    meta = get_asset(asset_symbol)
    if not address or not meta.address_validator:
        return False
    return meta.address_validator(address.strip())

def human_amount_from_base(amount_base_units: int | float, decimals: int) -> float:
    return float(amount_base_units) / (10 ** decimals)

def base_amount_from_human(amount_human: float, decimals: int) -> int:
    return int(round(float(amount_human) * (10 ** decimals)))
