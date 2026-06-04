from app.core.config import Settings


class TestSettings:
    def test_default_secret_key(self):
        s = Settings()
        assert s.SECRET_KEY == "change-me"

    def test_default_claude_api_key_empty(self):
        s = Settings()
        assert s.CLAUDE_API_KEY == ""

    def test_default_stripe_api_key_empty(self):
        s = Settings()
        assert s.STRIPE_API_KEY == ""

    def test_default_token_expiry(self):
        s = Settings()
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 7

    def test_default_database_url(self):
        s = Settings()
        assert "postgresql" in s.DATABASE_URL
