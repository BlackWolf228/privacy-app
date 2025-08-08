import asyncio
from uuid import UUID

import pytest
fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.main import app
from app.database import Base, get_db
from app.models.transaction import Transaction, TxType


@pytest.fixture
def client_and_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.get_event_loop().run_until_complete(init_db())

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c, TestingSessionLocal
    app.dependency_overrides.clear()
    asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_internal_transfer_creates_two_transactions(client_and_session):
    client, SessionLocal = client_and_session

    r1 = client.post("/auth/register", json={"email": "test1@test.com", "password": "strongpass"})
    assert r1.status_code == 200
    r2 = client.post("/auth/register", json={"email": "admin@example.com", "password": "strongpass"})
    assert r2.status_code == 200
    user2_id = r2.json()["id"]

    login = client.post("/auth/login", data={"username": "test1@test.com", "password": "strongpass"})
    assert login.status_code == 200
    token = login.json()["access_token"]

    payload = {"receiver_id": user2_id, "amount": "10", "currency": "EUR"}
    tr = client.post(
        "/wallets/transfer/internal",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tr.status_code == 200

    async def fetch_transactions():
        async with SessionLocal() as session:
            result = await session.execute(select(Transaction).order_by(Transaction.created_at))
            return result.scalars().all()

    txs = asyncio.get_event_loop().run_until_complete(fetch_transactions())
    assert len(txs) == 2
    assert txs[0].user_id == UUID(r1.json()["id"])
    assert txs[0].type == TxType.internal_out
    assert txs[1].user_id == UUID(user2_id)
    assert txs[1].type == TxType.internal_in
    assert txs[0].group_id == txs[1].group_id
