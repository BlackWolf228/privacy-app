import secrets
import uuid
from unittest.mock import AsyncMock

import pytest


def generate_code():
    return f"{secrets.randbelow(900000) + 100000:06d}"


def test_generate_code(monkeypatch):
    def fake_randbelow(n):
        assert n == 900000
        return 123

    monkeypatch.setattr(secrets, "randbelow", fake_randbelow)
    code = generate_code()
    assert code == "100123"
    assert len(code) == 6


def test_verify_code_rejects_email_mismatch():
    fastapi = pytest.importorskip("fastapi")
    from fastapi import HTTPException
    from app.models.user import User
    from app.routes.twofa import verify_code
    from app.schemas.twofa import EmailCodeVerify
    import asyncio

    user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash")
    payload = EmailCodeVerify(email="other@example.com", code="123456")
    db = AsyncMock()

    async def call():
        with pytest.raises(HTTPException) as exc_info:
            await verify_code(payload=payload, current_user=user, db=db)
        assert exc_info.value.status_code == 400
        assert "email" in exc_info.value.detail.lower()
        db.execute.assert_not_called()

    asyncio.run(call())
