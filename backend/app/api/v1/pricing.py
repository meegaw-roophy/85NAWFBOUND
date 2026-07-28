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
    'tier1': 15.49,
    'tier2': 44.99,
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

# ── FX rates (1 Unit of Local Currency = X USD) ────────
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
    days: int  # 30-366
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
    """Logarithmic commitment discount curve."""
    if days <= 30:
        return 0.0
    rate = ((days - 30) / 336) ** k / 6
    return rate  # Max ~16.67%

def get_milestone(days: int) -> Optional[dict]:
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
    Calculate final price for a given tier and duration with corrected currency conversions.
    """
    days = max(30, min(366, req.days))
    ppp = PPP_FACTORS.get(req.country_code, PPP_FACTORS['DEFAULT'])
    base_usd = BASE_USD_MONTHLY.get(req.tier, BASE_USD_MONTHLY['tier1'])
    
    # Apply PPP adjustments
    ppp_adjusted_usd = base_usd * ppp
    
    # CORRECTED: Convert from USD to Local Currency accurately
    currency = req.currency or 'USD'
    fx_rate = FX_RATES_TO_USD.get(currency, 1.0)
    monthly_local = ppp_adjusted_usd / fx_rate
    
    # Calculate subtotal (before commitment discounts)
    subtotal = monthly_local * days / 30.5
    
    # Calculate discount
    discount_rate = calculate_discount(days)
    discount_amount = subtotal * discount_rate
    discounted_subtotal = subtotal - discount_amount
    
    # Milestones and extended bonus days
    milestone = get_milestone(days)
    bonus_days = milestone['bonus_days'] if milestone else 0
    total_days = days + bonus_days
    
    # Tax math
    tax_rate = TAX_RATES.get(req.country_code, TAX_RATES['DEFAULT'])
    tax_amount = discounted_subtotal * tax_rate
    
    # Stripe payment gateway calculations
    stripe_fee_usd = (discounted_subtotal * fx_rate) * 0.029 + 0.30
    stripe_fee = stripe_fee_usd / fx_rate
    
    # Unified total configuration
    total = discounted_subtotal + tax_amount + stripe_fee
    
    # Retention metrics tracking
    full_price = monthly_local * days / 30.5
    saved_amount = full_price - total + (monthly_local * bonus_days / 30.5)
    monthly_equivalent = total / (total_days / 30.5)
    
    # Python 3.14 timezone compliance updates
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expires_at = now_utc + datetime.timedelta(days=total_days)
    expires_at = expires_at.replace(hour=23, minute=59, second=59)
    
    price_locked_until = (now_utc + datetime.timedelta(minutes=15)).isoformat()
    
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
    """Get available tiers with refined feature sets."""
    return {
        "tiers": [
            {
                "id": "free",
                "name": "Free Trial",
                "features": [
                    "7 days tracking access",
                    "Basic daily log variables",
                    "One automated trajectory preview",
                    "Real-time VEKTRA Score evaluation",
                ],
                "cta": "Current Plan"
            },
            {
                "id": "tier1",
                "name": "Vector Tier",
                "tagline": "For the focused builder",
                "features": [
                    "Unlimited daily telemetry input",
                    "Weekly harsh-truth AI data reports",
                    "Full direction angle (θ) score breakdown",
                    "Habit execution streak tracking",
                    "Personal financial trend engine",
                    "Complete timeline database logs",
                    "Priority server task execution queue",
                ],
                "cta": "Choose Vector"
            },
            {
                "id": "tier2",
                "name": "Apex Tier",
                "tagline": "For the serious operator",
                "features": [
                    "Everything included in the Vector plan",
                    "Monthly multi-variable strategic deep reports",
                    "Quarterly trajectory alignment auditing",
                    "Dynamic trend data visualizations",
                    "Personalized custom AI evaluation tone",
                    "Early prototype alpha feature testing privileges",
                    "Exclusive 👑 Founder baseline identification badge",
                ],
                "cta": "Choose Apex"
            }
        ],
        "milestones": MILESTONES
    }
