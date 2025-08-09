from typing import Any
from fastapi import Response, HTTPException
from fastapi.encoders import jsonable_encoder

def ok(data: Any, status: str = "ok"):
    return {"status": status, "data": data, "error": None}

def err(message: str, code: str = "bad_request", http_status: int = 400):
    raise HTTPException(
        status_code=http_status,
        detail={ "status": "error", "data": None, "error": {"code": code, "message": message} },
    )

def to_json(resp: Any, http_status: int = 200) -> Response:
    return Response(content=jsonable_encoder(resp), media_type="application/json", status_code=http_status)
