import time
from typing import Hashable, Tuple
from cachetools import TTLCache

fee_cache = TTLCache(maxsize=2048, ttl=60)

class SimpleRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.bucket: dict[Hashable, list[float]] = {}

    def allow(self, key: Hashable) -> bool:
        now = time.time()
        q = self.bucket.get(key, [])
        q = [t for t in q if now - t < self.window]
        if len(q) >= self.limit:
            self.bucket[key] = q
            return False
        q.append(now)
        self.bucket[key] = q
        return True

rate_limit_fee = SimpleRateLimiter(limit=10, window_seconds=60)

def fee_cache_key(asset: str, amount_human: float, dest_addr: str) -> Tuple[str, float, str]:
    amt = round(float(amount_human), 8)
    masked = f"{(dest_addr or '')[:4]}...{(dest_addr or '')[-4:]}" if dest_addr else ""
    return (asset, amt, masked)
