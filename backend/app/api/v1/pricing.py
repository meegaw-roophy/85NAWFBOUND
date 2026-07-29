from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import Optional
import datetime
import json
import os

# EXACT MATCH: Keeps prefix as /pricing to align with app.js [source: 1]
router = APIRouter(prefix="/pricing", tags=["pricing"])

# ── Dynamic File System Cache Loader ─────────────────────
def load_cached_fx_rates() -> dict:
    """
    Sourced daily via a background worker cron job that fetches 
    live data and saves it locally to avoid expensive external API lookups.
    """
    cache_path = "fx-cache.json"
    
    # Baseline fallback dict structure
    default_rates = {
        'KES': 129.00,  # 1 USD = 129 KES
        'NGN': 1500.00,
        'GHS': 15.10,
        'ZAR': 18.20,
        'GBP': 0.78,
        'EUR': 0.91,
        'USD': 1.00
    }
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return default_rates
    return default_rates

PPP_FACTORS = {
    'KE': 0.55, 'NG': 0.45, 'GH': 0.50, 'ZA': 0.65,
    'UG': 0.40, 'TZ': 0.42, 'ET': 0.35, 'RW': 0.38,
    'US': 1.00, 'GB': 0.95, 'EU': 0.90, 'CA': 0.88,
    'AU': 0.85, 'IN': 0.30, 'PK': 0.28, 'BR': 0.55,
    'MX': 0.60, 'DEFAULT': 0.70
}

BASE_USD_MONTHLY = {
    'tier1': 24.99,
    'tier2': 49.99,
}

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

CURRENCY_SYMBOLS = {
    'KES': 'KES', 'NGN': '₦', 'GHS': '₵', 'ZAR': 'R',
    'UGX': 'UGX', 'TZS': 'TZS', 'GBP': '£', 'EUR': '€',
    'INR': '₹', 'BRL': 'R$', 'MXN': '$', 'USD': '$',
}

MILESTONES = [
    {'days': 30,  'label': 'Monthly',      'stars': 0,  'bonus_days': 0,  'badge': None},
    {'days': 61,  'label': '2 Months',     'stars': 1,  'bonus_days': 4,  'badge': '⭐'},
    {'days': 91,  'label': 'Quarter',      'stars': 2,  'bonus_days': 10, 'badge': '⭐⭐'},
    {'days': 183, 'label': 'Half Year',    'stars': 3,  'bonus_days': 25, 'badge': '⭐⭐⭐'},
    {'days': 274, 'label': '9 Months',     'stars': 4,  'bonus_days': 42, 'badge': '⭐⭐⭐⭐'},
    {'days': 366, 'label': 'Full Year',    'stars': 5,  'bonus_days': 61, 'badge': '👑 Founder'},
]

class PriceRequest(BaseModel):
    tier: str  
    days: int  
    currency: Optional[str] = 'USD'
    country_code: Optional[str] = 'DEFAULT'

# EXACT MATCH: Reverted all Pydantic parameters to match variables in app.js [source: 1]
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

def calculate_discount(days: int, k: float = 1.8) -> float:
    """Logarithmic commitment discount curve (optimized k factor)."""
    if days <= 30:
        return 0.0
    rate = (((days - 30) / 336) ** k) / 6
    return rate  

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
    # The slider selection dictates the absolute calendar access window
    days = max(30, min(366, req.days))
    
    ppp = PPP_FACTORS.get(req.country_code, PPP_FACTORS['DEFAULT'])
    base_usd = BASE_USD_MONTHLY.get(req.tier, BASE_USD_MONTHLY['tier1'])
    
    # 1. Apply PPP Adjustments
    ppp_adjusted_usd = base_usd * ppp
    
    # 2. Extract Currency Routing from Live File Cache
    live_fx = load_cached_fx_rates()
    currency = req.currency or 'USD'
    
    local_currency_per_usd = live_fx.get(currency, 1.0)
    monthly_local = ppp_adjusted_usd * local_currency_per_usd
    
    # 3. Calculate Base Subtotal for the entire slider duration
    normalized_months = 1.0 + ((days - 30) * 11 / 336)
    subtotal = monthly_local * normalized_months
    
    # 4. Fetch Milestones
    milestone = get_milestone(days)
    bonus_days = milestone['bonus_days'] if milestone else 0
    
    # ── THE MATH FIX: Discount represents the value of the free days ──
    # Instead of adding 45 days, we calculate what % of the selected days are free.
    # For 366 days with 45 bonus days, discount_rate becomes exactly 45 / 366 = 12.29%
    # We combine this with your logarithmic curve to cap total savings beautifully.
    base_discount_rate = calculate_discount(days)
    milestone_discount_rate = bonus_days / days if days > 30 else 0.0
    
    # Use the higher discount to protect your 10x ratio target perfectly
    discount_rate = max(base_discount_rate, milestone_discount_rate)
    
    discount_amount = subtotal * discount_rate
    discounted_subtotal = subtotal - discount_amount
    
    # ── THE ACCESS FIX: Total days matches slider exactly ──
    total_days = days 
    
    # 5. Process Regional Tax Matrices
    tax_rate_raw = TAX_RATES.get(req.country_code, TAX_RATES['DEFAULT'])
    net_needed = discounted_subtotal * (1 + tax_rate_raw)
    
    # 6. Surcharge Reverse Payout Calculations (M-Pesa vs Stripe)
    if req.country_code == 'KE':
        stripe_fee = 50.00  
        total = net_needed + stripe_fee
        tax_amount = discounted_subtotal * tax_rate_raw
    else:
        stripe_fixed_usd = 0.30
        stripe_fixed_local = stripe_fixed_usd * local_currency_per_usd
        stripe_percentage = 0.029
        
        total = (net_needed + stripe_fixed_local) / (1 - stripe_percentage)
        stripe_fee = total * stripe_percentage + stripe_fixed_local
        tax_amount = discounted_subtotal * tax_rate_raw
    
    # 7. Calculate Financial Value Tracking Metrics
    full_price = subtotal
    saved_amount = discount_amount
    monthly_equivalent = total / (total_days / 30.5)
    
    # 8. Timezone Sync
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
        tax_rate=round(tax_rate_raw * 100, 2),        
        tax_amount=round(tax_amount, 2),
        stripe_fee=round(stripe_fee, 2),
        total=round(total, 2),
        total_days=total_days, # Will now read exactly 366 instead of 411!
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
