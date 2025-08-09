from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fee_ok():
    payload = {'asset':'BTC_TEST','amount':0.001,'destination_address':'tb1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqs3h5np'}
    r = client.post('/fees/estimate', json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    for k in ('low','medium','high','eta_seconds','units'):
        assert k in body['data']

def test_fee_invalid_address():
    payload = {'asset':'ETH','amount':1.0,'destination_address':'not_an_address'}
    r = client.post('/fees/estimate', json=payload)
    assert r.status_code == 400
    body = r.json()
    assert body['detail']['error']['code'] == 'bad_request'
