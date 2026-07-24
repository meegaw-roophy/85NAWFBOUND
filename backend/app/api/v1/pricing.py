from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import Optional
import datetime
import math

router = APIRouter(prefix="/pricing", tags=["pricing"])

# ── PPP factors by country ─────────────────────────────
PPP_FACTORS = {
    'KE': 0.55, 'NG': 0.45, 'GH': 0.50, 'ZA': 0.65,
    'UG': 0.40, 'TZ': 0.42, 'ET': 0.35, 'RW': 0.38,
    'US': 1.00, 'GB': 0.95, 'EU': 0.90, 'CA': 0.88,
    'AU': 0.85, 'IN': 0.30, 'PK': 0.28, 'BR': 0.55,
    'MX': 0.60, 'DEFAULT': 0.70
}

# ── Base USD prices per month ──────────────────────────
BASE_USD_MONTHLY = {
    'tier1': 3.99,
    'tier2': 14.99,
}

# ── Tax rates by country ───────────────────────────────
TAX_RATES = {
    'KE': 0.16,  # Kenya VAT 16%
    'ZA': 0.15,  # South Africa VAT 15%
    'NG': 0.075, # Nigeria VAT 7.5%
    'GH': 0.125, # Ghana VAT 12.5%
    'GB': 0.20,  # UK VAT 20%
    'DE': 0.19,  # Germany VAT 19%
    'FR': 0.20,  # France VAT 20%
    'DEFAULT': 0.00
}

# ── FX rates (cached daily — update via cron job later) ─
FX_RATES_TO_USD = {
    'KES': 0.00775,  # 1 KES = 0.00775 USD
    'NGN': 0.00065,
    'GHS': 0.067,
    'ZAR': 0.055,
    'UGX': 0.00027,
    'TZS': 0.00039,
    'GBP': 1.27,
    'EUR': 1.09,
    'INR': 0.012,
    'BRL': 0.18,
    'MXN': 0.058,
    'USD': 1.00,
}

# Currency symbols
CURRENCY_SYMBOLS = {
    'KES': 'KES', 'NGN': '₦', 'GHS': '₵', 'ZAR': 'R',
    'UGX': 'UGX', 'TZS': 'TZS', 'GBP': '£', 'EUR': '€',
    'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'USD': '$',
}

# Milestones for slider
MILESTONES = [
    {'days': 30,  'label': 'Monthly',      'stars': 0,  'bonus_days': 0,  'badge': None},
    {'days': 60,  'label': '2 Months',     'stars': 1,  'bonus_days': 3,  'badge': '⭐'},
    {'days': 90,  'label': 'Quarter',      'stars': 2,  'bonus_days': 7,  'badge': '⭐⭐'},
    {'days': 180, 'label': 'Half Year',    'stars': 3,  'bonus_days': 18, 'badge': '⭐⭐⭐'},
    {'days': 366, 'label': 'Full Year',    'stars': 4,  'bonus_days': 45, 'badge': '👑 Founder'},
]

class PriceRequest(BaseModel):
    tier: str  # 'tier1' or 'tier2'
    days: int  # 31-366
    currency: Optional[str] = 'USD'
    country_code: Optional[str] = 'DEFAULT'

class PriceResponse(BaseModel):
    tier: str
    days: int
    currency: str
    symbol: str
    subtotal: float
    discount_rate: float
    discount_amount: float
    bonus_days: int
    tax_rate: float
    tax_amount: float
    stripe_fee: float
    total: float
    total_days: int
    saved_amount: float
    monthly_equivalent: float
    expires_at: str
    milestone: Optional[dict] = None
    price_locked_until: str

def calculate_discount(days: int, k: float = 2.0) -> float:
    """Logarithmic discount curve. k=2.0 gives smooth reward for commitment."""
    if days <= 30:
        return 0.0
    # discount_rate = ((days - 30) / 336) ^ k / 6
    rate = ((days - 30) / 336) ** k / 6
    return rate  # Max ~16.67% (2 months free equivalent)

def get_milestone(days: int) -> Optional[dict]:
    """Get the milestone for a given day count."""
    current = None
    for m in MILESTONES:
        if days >= m['days']:
            current = m
    return current

@router.post("/calculate", response_model=PriceResponse)
async def calculate_price(
    req: PriceRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate final price for a given tier and duration.
    This is the ONLY source of truth for pricing — frontend never calculates final price.
    """
    # Clamp days
    days = max(30, min(366, req.days))
    
    # Get PPP factor
    ppp = PPP_FACTORS.get(req.country_code, PPP_FACTORS['DEFAULT'])
    
    # Get base USD monthly price
    base_usd = BASE_USD_MONTHLY.get(req.tier, BASE_USD_MONTHLY['tier1'])
    
    # Apply PPP
    ppp_adjusted_usd = base_usd * ppp
    
    # Convert to local currency
    currency = req.currency or 'USD'
    fx_rate = FX_RATES_TO_USD.get(currency, 1.0)
    monthly_local = ppp_adjusted_usd / fx_rate
    
    # Calculate subtotal (before discount)
    subtotal = monthly_local * days / 30.5
    
    # Calculate discount
    discount_rate = calculate_discount(days)
    discount_amount = subtotal * discount_rate
    discounted_subtotal = subtotal - discount_amount
    
    # Get milestone and bonus days
    milestone = get_milestone(days)
    bonus_days = milestone['bonus_days'] if milestone else 0
    total_days = days + bonus_days
    
    # Calculate tax
    tax_rate = TAX_RATES.get(req.country_code, TAX_RATES['DEFAULT'])
    tax_amount = discounted_subtotal * tax_rate
    
    # Stripe fee (2.9% + $0.30 converted to local)
    stripe_fee_usd = discounted_subtotal * fx_rate * 0.029 + 0.30
    stripe_fee = stripe_fee_usd / fx_rate
    
    # Final total
    total = discounted_subtotal + tax_amount + stripe_fee
    
    # What they save vs paying monthly
    full_price = monthly_local * days / 30.5
    saved_amount = full_price - total + (monthly_local * bonus_days / 30.5)
    
    # Monthly equivalent
    monthly_equivalent = total / (total_days / 30.5)
    
    # Expiry date
    expires_at = (datetime.datetime.utcnow() + datetime.timedelta(days=total_days))
    expires_at = expires_at.replace(hour=23, minute=59, second=59)
    
    # Price lock (15 minutes from now)
    price_locked_until = (datetime.datetime.utcnow() + datetime.timedelta(minutes=15)).isoformat()
    
    return PriceResponse(
        tier=req.tier,
        days=days,
        currency=currency,
        symbol=CURRENCY_SYMBOLS.get(currency, '$'),
        subtotal=round(subtotal, 2),
        discount_rate=round(discount_rate * 100, 2),
        discount_amount=round(discount_amount, 2),
        bonus_days=bonus_days,
        tax_rate=round(tax_rate * 100, 2),
        tax_amount=round(tax_amount, 2),
        stripe_fee=round(stripe_fee, 2),
        total=round(total, 2),
        total_days=total_days,
        saved_amount=round(max(saved_amount, 0), 2),
        monthly_equivalent=round(monthly_equivalent, 2),
        expires_at=expires_at.isoformat(),
        milestone=milestone,
        price_locked_until=price_locked_until,
    )

@router.get("/tiers")
async def get_tiers(current_user: User = Depends(get_current_user)):
    """Get available tiers and their features."""
    return {
        "tiers": [
            {
                "id": "free",
                "name": "Free",
                "features": [
                    "7 days tracking",
                    "Basic daily log",
                    "One taste report",
                    "VEKTRA score",
                ],
                "cta": "Current Plan"
            },
            {
                "id": "tier1",
                "name": "Vector",
                "tagline": "For the focused builder",
                "features": [
                    "Unlimited daily logging",
                    "Weekly AI reports",
                    "Full score breakdown",
                    "Streak tracking",
                    "Financial engine",
                    "Log history",
                    "Priority support",
                ],
                "cta": "Choose Vector"
            },
            {
                "id": "tier2",
                "name": "Apex",
                "tagline": "For the serious operator",
                "features": [
                    "Everything in Vector",
                    "Monthly deep reports",
                    "Quarterly strategy report",
                    "Annual video report",
                    "4K birthday card",
                    "Custom AI tone",
                    "Early feature access",
                    "Founder badge",
                ],
                "cta": "Choose Apex"
            }
        ],
        "milestones": MILESTONES
    }