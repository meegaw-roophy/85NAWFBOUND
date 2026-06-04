import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
)


class TestPasswordHashing:
    def test_hash_returns_string(self):
        h = get_password_hash("secret123")
        assert isinstance(h, str)
        assert h != "secret123"

    def test_verify_correct_password(self):
        h = get_password_hash("mypassword")
        assert verify_password("mypassword", h) is True

    def test_verify_wrong_password(self):
        h = get_password_hash("mypassword")
        assert verify_password("wrongpassword", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2


class TestAccessToken:
    def test_create_and_decode_token(self):
        token = create_access_token(subject="42")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_token_with_custom_expiry(self):
        token = create_access_token(subject="7", expires_delta=timedelta(minutes=1))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "7"

    def test_decode_invalid_token_returns_none(self):
        assert decode_access_token("not.a.valid.token") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token(subject="1")
        tampered = token[:-4] + "XXXX"
        assert decode_access_token(tampered) is None

    def test_expired_token_returns_none(self):
        token = create_access_token(
            subject="1", expires_delta=timedelta(seconds=-1)
        )
        assert decode_access_token(token) is None
