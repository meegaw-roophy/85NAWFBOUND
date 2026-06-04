import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas import (
    UserCreate,
    UserOut,
    SnapshotCreate,
    ReportCreate,
    SubscriptionCreate,
    StripePaymentRequest,
    MpesaPaymentRequest,
    Token,
)


class TestUserCreate:
    def test_valid_user(self):
        u = UserCreate(username="alice", email="alice@example.com", password="pass123")
        assert u.username == "alice"
        assert u.email == "alice@example.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(username="alice", email="not-an-email", password="pass")

    def test_missing_password_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(username="alice", email="alice@example.com")


class TestUserOut:
    def test_from_dict(self):
        u = UserOut(id=1, username="bob", email="bob@example.com", created_at=None)
        assert u.id == 1


class TestSnapshotCreate:
    def test_defaults(self):
        s = SnapshotCreate()
        assert s.timestamp is None
        assert s.mood is None
        assert s.income is None

    def test_with_values(self):
        now = datetime.utcnow()
        s = SnapshotCreate(timestamp=now, mood=8, energy=7, focus=6, income=100.0, expenses=50.0, savings=50.0)
        assert s.mood == 8
        assert s.income == 100.0


class TestReportCreate:
    def test_defaults(self):
        r = ReportCreate()
        assert r.period_start is None
        assert r.period_end is None


class TestSubscriptionCreate:
    def test_defaults(self):
        s = SubscriptionCreate(provider_customer_id="cus_1", plan="basic")
        assert s.provider == "stripe"
        assert s.active is True

    def test_custom_provider(self):
        s = SubscriptionCreate(provider="mpesa", provider_customer_id="cid", plan="premium", active=False)
        assert s.provider == "mpesa"
        assert s.active is False

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            SubscriptionCreate()


class TestStripePaymentRequest:
    def test_valid(self):
        r = StripePaymentRequest(customer_id="cus_123", price_id="price_abc")
        assert r.price_id == "price_abc"
        assert r.customer_id == "cus_123"

    def test_missing_price_id_rejected(self):
        with pytest.raises(ValidationError):
            StripePaymentRequest()


class TestMpesaPaymentRequest:
    def test_valid(self):
        r = MpesaPaymentRequest(phone_number="254712345678", amount=100.0)
        assert r.amount == 100.0

    def test_missing_phone_rejected(self):
        with pytest.raises(ValidationError):
            MpesaPaymentRequest(amount=100.0)


class TestToken:
    def test_defaults(self):
        t = Token(access_token="abc123")
        assert t.token_type == "bearer"
