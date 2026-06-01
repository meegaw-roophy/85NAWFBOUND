import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json().get("message")


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
