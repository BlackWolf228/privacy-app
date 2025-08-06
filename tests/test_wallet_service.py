import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_wallet_creation_via_endpoint(monkeypatch, client):
    from app.routes import wallets

    wallet_mock = AsyncMock(return_value={"currency": "btc", "network": "bitcoin"})
    monkeypatch.setattr(wallets, "create_wallet", wallet_mock)

    payload = {"currency": "btc", "network": "bitcoin"}
    response = client.post("/wallets", json=payload)
    assert response.status_code == 200
    wallet_mock.assert_awaited_once_with("btc", "bitcoin")


def test_wallet_requires_currency_and_network(client):
    r1 = client.post("/wallets", json={"currency": "btc"})
    assert r1.status_code == 422
    r2 = client.post("/wallets", json={"network": "bitcoin"})
    assert r2.status_code == 422
