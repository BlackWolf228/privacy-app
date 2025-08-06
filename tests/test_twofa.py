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


def test_verify_code_does_not_create_wallet(monkeypatch):
    fastapi = pytest.importorskip("fastapi")
    from app.models.user import User
    from app.models.twofa import EmailCode
    from app.routes.twofa import verify_code
    from app.schemas.twofa import EmailCodeVerify
    import asyncio
    from datetime import datetime, timedelta

    user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash")
    payload = EmailCodeVerify(email="user@example.com", code="123456")
    email_code = EmailCode(user_id=user.id, code="123456", expires_at=datetime.utcnow() + timedelta(minutes=5))

    db = AsyncMock()
    db.execute.return_value.scalar_one_or_none.return_value = email_code

    wallet_mock = AsyncMock()
    monkeypatch.setattr("app.routes.twofa.create_wallet", wallet_mock, raising=False)

    async def call():
        await verify_code(payload=payload, current_user=user, db=db)

    asyncio.run(call())
    wallet_mock.assert_not_called()
