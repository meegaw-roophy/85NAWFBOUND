import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.api.v1.pricing import calculate_discount, days_to_local_price

client = TestClient(app)

def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json().get("message")


def test_health():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_discount_curve_caps():
    assert calculate_discount(30, "tier1") == 0.0
    assert calculate_discount(366, "tier1") == pytest.approx(1 / 6)
    assert calculate_discount(366, "tier2") == pytest.approx(1 / 5)


def test_pricing_uses_simple_total_and_savings():
    result = days_to_local_price(days=30, tier="tier1", country_code="US", currency="USD")
    assert result["discount_rate_pct"] == 0.0
    assert result["you_save"] == 0.0
    assert result["total"] == pytest.approx(result["full_price"])
