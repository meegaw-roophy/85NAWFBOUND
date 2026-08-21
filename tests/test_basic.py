import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.api.v1.pricing import calculate_discount, days_to_local_price, local_price_to_days
from app.schemas import StripePaymentRequest, PaystackPaymentRequest
from app.services.paystack_service import verify_webhook_signature

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


def test_amount_pricing_round_trips_forward_curve():
    for days in (30, 61, 183, 366):
        amount = days_to_local_price(days, "tier1", "US", "USD")["total"]
        assert local_price_to_days(amount, "tier1", "US", "USD") == days


def test_payment_requests_accept_tier_metadata():
    stripe_req = StripePaymentRequest(customer_id="cus_123", price_id="price_123", tier="tier2")
    paystack_req = PaystackPaymentRequest(email="user@example.com", amount=1500, currency="KES", tier="tier1")

    assert stripe_req.tier == "tier2"
    assert paystack_req.tier == "tier1"


def test_paystack_request_accepts_quick_money_offer():
    request = PaystackPaymentRequest(
        email="user@example.com", amount=60, currency="USD", special_offer=True
    )
    assert request.special_offer is True


def test_paystack_signature_verification():
    secret = "paystack-secret"
    payload = b'{"event":"charge.success","data":{"reference":"ref_123"}}'
    import hmac
    import hashlib
    signature = hmac.new(secret.encode(), payload, hashlib.sha512).hexdigest()

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "bad-signature", secret) is False
