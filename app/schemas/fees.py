from pydantic import BaseModel, Field, validator
from app.core.assets import get_asset, validate_destination

class FeeEstimateRequest(BaseModel):
    asset: str = Field(..., description="e.g., BTC_TEST, ETH, USDT_ERC20")
    amount: float = Field(..., gt=0, description="Human-readable amount, e.g., 0.01")
    destination_address: str = Field(...)

    @validator("asset")
    def _asset_supported(cls, v):
        get_asset(v)
        return v

    @validator("destination_address")
    def _addr_ok(cls, v, values):
        asset = values.get("asset")
        if asset and not validate_destination(asset, v):
            raise ValueError("Invalid destination address for selected asset/network")
        return v

class FeeQuote(BaseModel):
    units: str
    low: float
    medium: float
    high: float
    eta_seconds: int
