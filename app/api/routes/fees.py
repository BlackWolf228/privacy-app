from fastapi import APIRouter, Depends, Request
from app.core.responses import ok, err
from app.core.limits import rate_limit_fee
from app.schemas.fees import FeeEstimateRequest
from app.services.fees import estimate_fee, FireblocksError

try:
    from app.core.auth import get_current_user
except Exception:
    def get_current_user():
        return None

router = APIRouter(prefix='/fees', tags=['fees'])

@router.post('/estimate')
def estimate_transaction_fee(payload: FeeEstimateRequest, request: Request, user = Depends(get_current_user)):
    key = getattr(user, 'id', None) or request.client.host or 'anon'
    if not rate_limit_fee.allow(key):
        return err('Too many requests. Please slow down.', code='rate_limited', http_status=429)
    try:
        quote = estimate_fee(payload)
        return ok(quote.dict())
    except FireblocksError as e:
        code = (e.code or '').lower()
        if code in ('insufficient_funds','balance_too_low'):
            return err('Insufficient balance for fee.', code='insufficient_funds', http_status=402)
        if code in ('asset_not_supported','invalid_destination'):
            return err('Invalid request for asset/destination.', code='invalid_request', http_status=400)
        if code in ('rate_limited','too_many_requests'):
            return err('Upstream rate limited.', code='upstream_rate_limited', http_status=429)
        return err('Upstream provider error.', code='upstream_error', http_status=502)
    except ValueError as ve:
        return err(str(ve), code='bad_request', http_status=400)
    except Exception:
        return err('Unexpected error.', code='internal_error', http_status=500)
