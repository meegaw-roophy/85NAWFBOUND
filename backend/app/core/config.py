from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_env_file() -> str | None:
    candidates = [
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path.cwd() / ".env",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ".env"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/vektra"
    CLAUDE_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    SECRET_KEY: str = "change-me"
    PAYSTACK_SECRET_KEY: str = ""
    PAYSTACK_PUBLIC_KEY: str = ""
    PAYSTACK_WEBHOOK_SECRET: str = ""
    GOOGLE_CLIENT_ID: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # one week

    # ── Referral commissions + refunds ────────────────────────
    REFERRAL_COMMISSION_HOLD_DAYS: int = 10
    REFUND_WINDOW_DAYS: int = 10  # deliberately equal to the hold above - see referral_commission_service.py
    REFERRAL_MIN_WITHDRAWAL_USD_EQUIVALENT: float = 10.0
    REFERRAL_COMMISSION_BONUS_CREDITS: int = 5  # flat VekCredit "gift" layered on top of cash, not tuned

    model_config = SettingsConfigDict(env_file=_detect_env_file(), env_file_encoding="utf-8")


settings = Settings()


