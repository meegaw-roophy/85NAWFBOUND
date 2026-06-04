import pytest
from unittest.mock import patch
from app.services.payment_service import (
    create_stripe_subscription,
    initiate_mpesa_payment,
)


class TestCreateStripeSubscription:
    def test_no_api_key_returns_failed(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.STRIPE_API_KEY = ""
            result = create_stripe_subscription("cus_123", "price_abc")
        assert result["status"] == "failed"
        assert result["reason"] == "stripe_api_key_not_configured"
        assert result["customer_id"] == "cus_123"
        assert result["price_id"] == "price_abc"

    def test_with_api_key_returns_success(self):
        with patch("app.services.payment_service.settings") as mock_settings:
            mock_settings.STRIPE_API_KEY = "sk_test_xxx"
            result = create_stripe_subscription("cus_123", "price_abc")
        assert result["status"] == "success"
        assert result["provider"] == "stripe"
        assert result["customer_id"] == "cus_123"
        assert result["price_id"] == "price_abc"


class TestInitiateMpesaPayment:
    def test_valid_amount_queued(self):
        result = initiate_mpesa_payment("254712345678", 500.0)
        assert result["status"] == "queued"
        assert result["provider"] == "mpesa"
        assert result["phone_number"] == "254712345678"
        assert result["amount"] == 500.0

    def test_zero_amount_fails(self):
        result = initiate_mpesa_payment("254712345678", 0)
        assert result["status"] == "failed"
        assert result["reason"] == "invalid_amount"

    def test_negative_amount_fails(self):
        result = initiate_mpesa_payment("254712345678", -10)
        assert result["status"] == "failed"
        assert result["reason"] == "invalid_amount"
