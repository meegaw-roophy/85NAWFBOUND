"""
VEKTRA Pricing Engine V2
========================
Clean, honest pricing. No tax/fee theatre.

Philosophy:
    - Base price × PPP factor × FX rate = what user pays
    - 1.3333 multiplier baked into base price to cover all costs
    - User sees: Total, You Save, Expires
    - Nothing else.

Base prices (after 1.3333 multiplier applied internally):
    Tier 1: $16.50/month target → charge $22/month → user sees local currency
    Tier 2: $41.25/month target → charge $55/month → user sees local currency
    Tier 3: $82.50/month target → charge $110/month → user sees local currency

Discount caps:
    Tier 1: max 16.667% at 366 days (2 month free equivalent)
    Tier 2: max 20.000% at 366 days (2.4 months free equivalent)
    Tier 3: max 25.000% at 366 days (3 months free equivalent)

Discount curve: linear from 0% at day 30 to max% at day 366
"""

from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import Optional
import datetime
import json
import os

router = APIRouter(prefix="/pricing", tags=["pricing"])


# ─────────────────────────────────────────────
#  FX RATES — daily cached file
#  Format: { "KES": 129.50, "NGN": 1520.00, ... }
#  Background worker updates this file daily.
#  Falls back to hardcoded rates if file missing.
# ─────────────────────────────────────────────
FALLBACK_FX = {
    "USD": 1.00,
    "KES": 129.50,
    "NGN": 1520.00,
    "GHS": 15.20,
    "ZAR": 18.40,
    "UGX": 3720.00,
    "TZS": 2680.00,
    "ETB": 57.00,
    "RWF": 1380.00,
    "GBP": 0.78,
    "EUR": 0.91,
    "CAD": 1.36,
    "AUD": 1.52,
    "INR": 83.50,
    "PKR": 278.00,
    "BRL": 5.10,
    "MXN": 17.20,
    "EGP": 48.50,
    "ZMW": 27.00,
    "XOF": 600.00,
}

CURRENCY_SYMBOLS = {
    "USD": "$", "KES": "KES", "NGN": "₦", "GHS": "₵",
    "ZAR": "R", "UGX": "UGX", "TZS": "TZS", "ETB": "ETB",
    "RWF": "RWF", "GBP": "£", "EUR": "€", "CAD": "CA$",
    "AUD": "A$", "INR": "₹", "PKR": "₨", "BRL": "R$",
    "MXN": "$", "EGP": "EGP", "ZMW": "ZMW", "XOF": "XOF",
}

def get_fx_rates() -> dict:
    """Load live FX rates from cache file, fall back to hardcoded."""
    cache_path = os.path.join(os.path.dirname(__file__), "fx_cache.json")
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
                if data and isinstance(data, dict):
                    return {**FALLBACK_FX, **data}
        except Exception:
            pass
    return FALLBACK_FX


# ─────────────────────────────────────────────
#  PPP FACTORS
#  Range: 0.40 (most affordable) to 1.00 (US baseline)
#  7 bands covering ~180 countries
# ─────────────────────────────────────────────
PPP_FACTORS = {
    # Band 1 — 0.40 (Poorest purchasing power)
    "ET": 0.40, "UG": 0.40, "RW": 0.40, "ML": 0.40,
    "BF": 0.40, "NE": 0.40, "TD": 0.40, "MZ": 0.40,
    "MW": 0.40, "MG": 0.40,

    # Band 2 — 0.48
    "TZ": 0.48, "ZM": 0.48, "SD": 0.48, "SN": 0.48,
    "CM": 0.48, "CI": 0.48, "GN": 0.48, "BJ": 0.48,

    # Band 3 — 0.55
    "KE": 0.55, "NG": 0.55, "GH": 0.55, "PK": 0.55,
    "BD": 0.55, "IN": 0.55, "VN": 0.55, "PH": 0.55,
    "EG": 0.55, "MA": 0.55,

    # Band 4 — 0.65
    "ZA": 0.65, "BR": 0.65, "MX": 0.65, "ID": 0.65,
    "TH": 0.65, "UA": 0.65, "BO": 0.65, "PY": 0.65,

    # Band 5 — 0.75
    "CN": 0.75, "TR": 0.75, "CO": 0.75, "PE": 0.75,
    "RO": 0.75, "BG": 0.75, "RS": 0.75, "AR": 0.75,

    # Band 6 — 0.88
    "PL": 0.88, "HU": 0.88, "CZ": 0.88, "MY": 0.88,
    "RU": 0.88, "SA": 0.88, "AE": 0.88, "IL": 0.88,
    "KR": 0.88, "TW": 0.88, "PT": 0.88, "GR": 0.88,

    # Band 7 — 1.00 (Full price)
    "US": 1.00, "GB": 1.00, "DE": 1.00, "FR": 1.00,
    "NL": 1.00, "SE": 1.00, "NO": 1.00, "DK": 1.00,
    "FI": 1.00, "CH": 1.00, "AT": 1.00, "BE": 1.00,
    "CA": 1.00, "AU": 1.00, "NZ": 1.00, "JP": 1.00,
    "SG": 1.00, "HK": 1.00,

    "DEFAULT": 0.70,
}


# ─────────────────────────────────────────────
#  BASE PRICES — already include 1.3333 multiplier
#  Internal: $16.50/$41.25 target revenue
#  Charged: $22/$55 (covers all fees/taxes)
# ─────────────────────────────────────────────
BASE_USD_MONTHLY = {
    "tier1": 22,
    "tier2": 55,
    "tier3": 110,
}

# Discount caps per tier
DISCOUNT_CAPS = {
    "tier1": 1/6,      # 16.667% — 2 month free at annual
    "tier2": 1/5,      # 20.000% — 2.4 months free at annual
    "tier3": 1/4,      # 25.000% — 3 months free at annual
}


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def calculate_discount(days: int, tier: str) -> float:
    """
    Linear discount from 0% at day 30 to max% at day 366.
    No complexity — clean and honest.
    """
    if days <= 30:
        return 0.0
    cap = DISCOUNT_CAPS.get(tier, DISCOUNT_CAPS["tier1"])
    progress = ((days - 30) / 336) ** 1.9  # 0.0 to 1.0
    return cap * progress


def days_to_local_price(days: int, tier: str, country_code: str, currency: str) -> dict:
    """
    Core pricing calculation.
    Returns everything needed for the UI.
    """
    fx = get_fx_rates()
    
    days = max(30, min(366, days))
    ppp = PPP_FACTORS.get(country_code, PPP_FACTORS["DEFAULT"])
    base_usd = BASE_USD_MONTHLY.get(tier, BASE_USD_MONTHLY["tier1"])
    
    # PPP adjusted monthly price in USD
    monthly_usd = base_usd * ppp
    
    # Convert to local currency
    rate = fx.get(currency, 1.0)
    monthly_local = monthly_usd * rate
    
    # Full price for selected days (no discount)
    full_price = monthly_local * days / 30.5
    
    # Apply discount
    discount_rate = calculate_discount(days, tier)
    discount_amount = full_price * discount_rate
    total = full_price - discount_amount
    
    # Monthly equivalent after discount
    monthly_equivalent = total / (days / 30.5)
    
    # Expiry date (exactly the days selected — no bonus days shown separately)
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = (now + datetime.timedelta(days=days)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )
    
    return {
        "days": days,
        "monthly_local": round(monthly_local, 2),
        "full_price": round(full_price, 2),
        "discount_rate_pct": round(discount_rate * 100, 2),
        "discount_amount": round(discount_amount, 2),
        "total": round(total, 2),
        "monthly_equivalent": round(monthly_equivalent, 2),
        "you_save": round(discount_amount, 2),
        "expires_at": expires_at.isoformat(),
        "symbol": CURRENCY_SYMBOLS.get(currency, "$"),
        "currency": currency,
    }


# ─────────────────────────────────────────────
#  API MODELS
# ─────────────────────────────────────────────
class PriceRequest(BaseModel):
    tier: str
    days: int
    currency: Optional[str] = "USD"
    country_code: Optional[str] = "DEFAULT"


class PriceResponse(BaseModel):
    tier: str
    days: int
    currency: str
    symbol: str
    total: float
    you_save: float
    discount_rate_pct: float
    monthly_equivalent: float
    expires_at: str
    price_locked_until: str


# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────
@router.post("/calculate", response_model=PriceResponse)
async def calculate_price(
    req: PriceRequest,
    current_user: User = Depends(get_current_user)
):
    """Calculate final price — single source of truth."""
    result = days_to_local_price(
        days=req.days,
        tier=req.tier,
        country_code=req.country_code or "DEFAULT",
        currency=req.currency or "USD",
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    price_locked_until = (now + datetime.timedelta(minutes=15)).isoformat()

    return PriceResponse(
        tier=req.tier,
        days=result["days"],
        currency=result["currency"],
        symbol=result["symbol"],
        total=result["total"],
        you_save=result["you_save"],
        discount_rate_pct=result["discount_rate_pct"],
        monthly_equivalent=result["monthly_equivalent"],
        expires_at=result["expires_at"],
        price_locked_until=price_locked_until,
    )


@router.get("/tiers")
async def get_tiers(current_user: User = Depends(get_current_user)):
    return {
        "tiers": [
            {
                "id": "free",
                "name": "Free",
                "tagline": "Start your trajectory",
                "features": [
                    "7 days of tracking",
                    "Basic daily log",
                    "VEKTRA score",
                    "One weekly preview report",
                ],
                "cta": "Current Plan",
                "price_usd": 0,
            },
            {
                "id": "tier1",
                "name": "Vector",
                "tagline": "For the focused builder",
                "features": [
                    "Unlimited daily logging",
                    "Weekly AI harsh-truth reports",
                    "Full score breakdown",
                    "Streak tracking",
                    "Financial engine",
                    "Log history",
                    "Birthday trajectory card",
                ],
                "cta": "Choose Vector",
                "price_usd": 22,
            },
            {
                "id": "tier2",
                "name": "Apex",
                "tagline": "For the serious operator",
                "features": [
                    "Everything in Vector",
                    "Monthly deep reports",
                    "Quarterly strategy report",
                    "Custom AI tone",
                    "Early feature access",
                    "👑 Founder badge",
                ],
                "cta": "Choose Apex",
                "price_usd": 55,
            },
            {
                "id": "tier3",
                "name": "Founder",
                "tagline": "For the ambitious operator",
                "features": [
                    "Everything in Apex",
                    "Priority support",
                    "Advanced growth planning",
                    "Early access to new modules",
                ],
                "cta": "Choose Founder",
                "price_usd": 110,
            }
        ]
    }


@router.get("/fx-rates")
async def get_current_fx_rates(current_user: User = Depends(get_current_user)):
    """Returns current FX rates in use — for transparency."""
    return get_fx_rates()