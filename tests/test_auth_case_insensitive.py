import asyncio
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

@pytest.fixture
def client():
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
        yield c
    app.dependency_overrides.clear()
    asyncio.get_event_loop().run_until_complete(engine.dispose())


def test_registration_is_case_insensitive(client):
    payload = {"email": "TEST1@TEST.COM", "password": "strongpass"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200
    assert r.json()["email"] == "test1@test.com"

    r2 = client.post("/auth/register", json={"email": "test1@test.com", "password": "strongpass"})
    assert r2.status_code == 400

def test_login_is_case_insensitive(client):
    payload = {"email": "test1@test.com", "password": "strongpass"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200

    r2 = client.post("/auth/login", data={"username": "TEST1@TEST.COM", "password": "strongpass"})
    assert r2.status_code == 200
    assert "access_token" in r2.json()
