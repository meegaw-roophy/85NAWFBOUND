import secrets as _secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


def _generate_secret_key() -> str:
    """Generate a cryptographically secure default so the app never runs with a known key."""
    return _secrets.token_urlsafe(32)


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/vektra"
    CLAUDE_API_KEY: str = ""
    STRIPE_API_KEY: str = ""
    SECRET_KEY: str = _generate_secret_key()
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALLOWED_CORS_ORIGINS: str = "http://localhost:8001,http://127.0.0.1:8001"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
