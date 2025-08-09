from typing import Tuple
from app.core.assets import get_asset, human_amount_from_base
from app.core.limits import fee_cache, fee_cache_key
from app.schemas.fees import FeeEstimateRequest, FeeQuote

class FireblocksError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

def _call_fireblocks_estimate(req: FeeEstimateRequest) -> Tuple[int,int,int,int]:
    # TODO: Înlocuiește cu apelul real la Fireblocks (operation=TRANSFER + destination)
    base_low = 1000
    base_med = 2000
    base_high = 3000
    eta = 60
    return base_low, base_med, base_high, eta

def estimate_fee(req: FeeEstimateRequest) -> FeeQuote:
    meta = get_asset(req.asset)
    ck = fee_cache_key(req.asset, req.amount, req.destination_address)

    if ck in fee_cache:
        return fee_cache[ck]

    base_low, base_med, base_high, eta = _call_fireblocks_estimate(req)

    quote = FeeQuote(
        units=meta.symbol,
        low=human_amount_from_base(base_low, meta.decimals),
        medium=human_amount_from_base(base_med, meta.decimals),
        high=human_amount_from_base(base_high, meta.decimals),
        eta_seconds=eta,
    )
    fee_cache[ck] = quote
    return quote
