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
    Tier 1: $15.00/month target → charge $20/month → user sees local currency
    Tier 2: $37.50/month target → charge $50/month → user sees local currency
    Tier 3: $75.00/month target → charge $100/month → user sees local currency

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
    "tier1": 20,
    "tier2": 50,
    "tier3": 100,
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
    Discount formula: ((((days-30)/336)^k)/m)
    k = 1.9 (between 1.5-2.0)
    m = 6 for tier1 (Vector), 5 for tier2 (Apex)
    """
    if days <= 30:
        return 0.0
    
    k = 1.9
    m = 6 if tier == "tier1" else 5 if tier == "tier2" else 4
    progress = ((days - 30) / 336) ** k
    discount_rate = progress / m
    return discount_rate  # Cap at 25%


def calculate_bonus_days(discount_rate: float, days: int) -> int:
    """
    Calculate bonus days from discount rate.
    Bonus days = discount_rate * days (the free days equivalent to the discount)
    """
    return int(discount_rate * days)


def days_to_local_price(days: int, tier: str, country_code: str, currency: str) -> dict:
    """
    Core pricing calculation.
    
    Handles exact 30-day requests as exactly 1 month without 30.5 scaling factors,
    and applies the fractional formula for any period from 31 to 366 days.
    """
    fx = get_fx_rates()
    
    # Restrict input bounds between 30 and 366 days
    days = max(30, min(366, days))
    
    ppp = PPP_FACTORS.get(country_code, PPP_FACTORS["DEFAULT"])
    base_usd = BASE_USD_MONTHLY.get(tier, BASE_USD_MONTHLY["tier1"])
    
    # PPP adjusted monthly price in USD (X)
    monthly_usd = base_usd * ppp
    
    # Convert to local currency
    rate = fx.get(currency, 1.0)
    monthly_local = monthly_usd * rate  # This is X in local currency
    
    # Fetch discount rate based on active tier and days
    discount_rate = calculate_discount(days, tier)
    
    # --- CONDITION CONDITIONAL SPLIT ---
    if days == 30:
        # Treat exactly 30 days as exactly 1 flat month (No 30.5 fraction factors)
        full_price = monthly_local
        total = monthly_local
        monthly_equivalent = total
    else:
        # For 31 to 366 days, apply the original 30.5 fraction factors (2 / 61)
        full_price = monthly_local * days * 2 / 61
        total = full_price * (1 - discount_rate)
        monthly_equivalent = total / (days / 30.5)
    
    # Calculate discount savings
    discount_amount = full_price - total
    
    # Calculate bonus days from discount rate
    bonus_days = calculate_bonus_days(discount_rate, days)
    
    # Expiry date calculation
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
        "bonus_days": bonus_days,
        "expires_at": expires_at.isoformat(),
        "symbol": CURRENCY_SYMBOLS.get(currency, "$"),
        "currency": currency,
    }


def local_price_to_days(amount: float, tier: str, country_code: str, currency: str) -> int:
    """Find the integer duration whose forward price is closest to an amount.

    The discount term contains ``days`` both linearly and as a power, so there
    is no useful elementary closed-form solution. Binary search is exact for
    the monotonic forward pricing curve and keeps both directions consistent.
    """
    low, high = 30, 366
    while low <= high:
        middle = (low + high) // 2
        total = days_to_local_price(middle, tier, country_code, currency)["total"]
        if total < amount:
            low = middle + 1
        elif total > amount:
            high = middle - 1
        else:
            return middle

    candidates = [max(30, min(366, low)), max(30, min(366, high))]
    return min(
        candidates,
        key=lambda days: abs(
            days_to_local_price(days, tier, country_code, currency)["total"] - amount
        ),
    )

# ─────────────────────────────────────────────
#  API MODELS
# ─────────────────────────────────────────────
class PriceRequest(BaseModel):
    tier: str
    days: Optional[int] = None
    amount: Optional[float] = None
    currency: Optional[str] = "USD"
    country_code: Optional[str] = "DEFAULT"
    special_offer: Optional[bool] = False  # Quick Money Strategy offer


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
    bonus_days: int


# ─────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────
@router.post("/calculate", response_model=PriceResponse)
async def calculate_price(
    req: PriceRequest,
    current_user: User = Depends(get_current_user)
):
    """Calculate final price — single source of truth."""
    
    # Check if special offer is active
    campaign_timezone = datetime.timezone(datetime.timedelta(hours=3))
    SPECIAL_OFFER_DEADLINE = datetime.datetime(2026, 9, 9, 23, 59, 59, tzinfo=campaign_timezone)
    now = datetime.datetime.now(campaign_timezone)
    is_special_offer_active = req.special_offer and now < SPECIAL_OFFER_DEADLINE
    
    # If special offer is active, force 120 days (4 months) and apply 25% discount
    if is_special_offer_active:
        req.days = 120  # 4 months (3 paid + 1 free)
    
    # Quick Money is a fixed campaign product: charge three months and grant
    # four months of access. It must not use the normal day/amount calculator.
    if is_special_offer_active:
        monthly_price = days_to_local_price(
            30, req.tier, req.country_code or "DEFAULT", req.currency or "USD"
        )
        result = {**monthly_price}
        result["days"] = 120
        result["full_price"] = round(monthly_price["monthly_local"] * 4, 2)
        result["total"] = round(monthly_price["monthly_local"] * 3, 2)
        result["discount_amount"] = round(result["full_price"] - result["total"], 2)
        result["you_save"] = result["discount_amount"]
        result["discount_rate_pct"] = 25.0
        result["monthly_equivalent"] = round(result["total"] / 4, 2)
        result["bonus_days"] = 30

    # If amount is provided, calculate days from the same forward curve.
    elif req.amount is not None:
        minimum_amount = days_to_local_price(
            30, req.tier, req.country_code or "DEFAULT", req.currency or "USD"
        )["total"]
        maximum_amount = days_to_local_price(
            366, req.tier, req.country_code or "DEFAULT", req.currency or "USD"
        )["total"]
        requested_amount = max(minimum_amount, min(maximum_amount, req.amount))
        days = local_price_to_days(
            amount=requested_amount,
            tier=req.tier,
            country_code=req.country_code or "DEFAULT",
            currency=req.currency or "USD",
        )
        result = days_to_local_price(
            days=days,
            tier=req.tier,
            country_code=req.country_code or "DEFAULT",
            currency=req.currency or "USD",
        )
        
        # The entered amount is the checkout amount; derive the displayed
        # savings from that amount and the resolved duration.
        result["total"] = round(requested_amount, 2)
        result["discount_amount"] = round(result["full_price"] - result["total"], 2)
        result["you_save"] = result["discount_amount"]
        result["discount_rate_pct"] = round(
            (result["discount_amount"] / result["full_price"]) * 100
            if result["full_price"] else 0,
            2,
        )
        result["monthly_equivalent"] = round(result["total"] / (days / 30.5), 2)
        
    else:
        # Original days-based calculation
        result = days_to_local_price(
            days=req.days or 30,
            tier=req.tier,
            country_code=req.country_code or "DEFAULT",
            currency=req.currency or "USD",
        )
        
    # Set expiry date to Jan 1, 2027 for special offer, otherwise normal calculation
    if is_special_offer_active:
        expires_at = datetime.datetime(2027, 1, 1, 23, 59, 59, tzinfo=campaign_timezone).isoformat()
    else:
        expires_at = result["expires_at"]
    
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
        expires_at=expires_at,
        price_locked_until=price_locked_until,
        bonus_days=result["bonus_days"],
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
                "price_usd": 20,
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
                "price_usd": 50,
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
                "price_usd": 100,
            }
        ]
    }


@router.get("/fx-rates")
async def get_current_fx_rates(current_user: User = Depends(get_current_user)):
    """Returns current FX rates in use — for transparency."""
    return get_fx_rates()