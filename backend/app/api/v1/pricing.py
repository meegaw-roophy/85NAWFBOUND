from fastapi import APIRouter, Depends, HTTPException
from app.core.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import Optional
import datetime
import json
import os

router = APIRouter(prefix="/pricing", tags=["pricing"])

# ── Production-Grade Dynamic Cache Loader ────────────────
def load_cached_fx_rates() -> dict:
    """
    Sourced daily via a background worker cron job that fetches 
    live data and saves it locally to avoid expensive external API lookups.
    """
    cache_path = "fx-cache.json"
    
    # Fallback production baselines if local filesystem sync breaks
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

PPP_FACTORS = {'KE': 0.55, 'NG': 0.45, 'GH': 0.50, 'ZA': 0.65, 'US': 1.00, 'DEFAULT': 0.70}
BASE_USD_MONTHLY = {'tier1': 15.49, 'tier2': 44.99}
TAX_RATES = {'KE': 0.16, 'ZA': 0.15, 'NG': 0.075, 'GH': 0.125, 'GB': 0.20, 'DEFAULT': 0.00}
CURRENCY_SYMBOLS = {'KES': 'KES', 'NGN': '₦', 'GHS': '₵', 'ZAR': 'R', 'GBP': '£', 'EUR': '€', 'USD': '$'}

class SliderCalculationRequest(BaseModel):
    tier: str
    days: int
    country_code: str

class PriceResponse(BaseModel):
    tier: str
    days_selected: int
    bonus_days: int
    total_access_days: int
    currency: str
    symbol: str
    badge: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    gateway_fee: float
    total_checkout_amount: float
    expires_at: str
    price_locked_until: str

@router.post("/calculate", response_model=PriceResponse)
async def preview_slider_price(
    req: SliderCalculationRequest, 
    current_user: User = Depends(get_current_user)
):
    """
    Triggered instantly by frontend JavaScript animations every time the user moves the slider.
    Calculates numbers completely server-side to prevent client manipulation.
    """
    if req.days < 30 or req.days > 366:
        raise HTTPException(status_code=400, detail="Commitment window must be between 30 and 366 days.")
        
    if req.tier not in BASE_USD_MONTHLY:
        raise HTTPException(status_code=400, detail="Invalid target tier selected.")

    # 1. Evaluate PPP Basis
    country = req.country_code.upper()
    ppp = PPP_FACTORS.get(country, PPP_FACTORS['DEFAULT'])
    base_usd = BASE_USD_MONTHLY[req.tier]
    ppp_adjusted_usd = base_usd * ppp

    # 2. Extract Currency Routing
    currency_map = {'KE': 'KES', 'NG': 'NGN', 'GH': 'GHS', 'ZA': 'ZAR', 'US': 'USD'}
    currency = currency_map.get(country, 'USD')
    
    fx_rates = load_cached_fx_rates()
    local_currency_per_usd = fx_rates.get(currency, 1.0)
    
    # Base monthly price in local currency after PPP conversion
    monthly_local = ppp_adjusted_usd * local_currency_per_usd
    
    # 3. Apply Logarithmic Discount Curve (k = 1.8 for balanced commitment optimization)
    k = 1.8 
    discount_rate = 0.0
    if req.days > 30:
        discount_rate = (((req.days - 30) / 336) ** k) / 6  # Caps beautifully near ~16.67%

    subtotal_local = monthly_local * (req.days / 30.5)
    discount_amount_local = subtotal_local * discount_rate
    discounted_subtotal = subtotal_local - discount_amount_local

    # 4. Tax Routing Matrix
    tax_rate = TAX_RATES.get(country, TAX_RATES['DEFAULT'])
    net_needed_with_tax = discounted_subtotal * (1 + tax_rate)

    # 5. Gateway Surcharge Engineering (Stripe Pass-Through vs M-Pesa)
    if country == 'KE':
        gateway_fee = 50.00  # Local carrier insurance markup
        total_charged = net_needed_with_tax + gateway_fee
        tax_amount = discounted_subtotal * tax_rate
    else:
        # Global Stripe Absorption Formula to guarantee 100% net payout preservation
        stripe_fixed_usd = 0.30
        stripe_fixed_local = stripe_fixed_usd * local_currency_per_usd
        stripe_percentage = 0.029
        
        total_charged = (net_needed_with_tax + stripe_fixed_local) / (1 - stripe_percentage)
        gateway_fee = total_charged * stripe_percentage + stripe_fixed_local
        tax_amount = discounted_subtotal * tax_rate

    # 6. Time and Milestones Configuration
    bonus_days = 0
    badge = "Hobbyist"
    if req.days >= 366: bonus_days = 45; badge = "👑 Founder"
    elif req.days >= 180: bonus_days = 18; badge = "⭐⭐⭐ Operator"
    elif req.days >= 90: bonus_days = 7; badge = "⭐⭐ Builder"
    elif req.days >= 60: bonus_days = 3; badge = "⭐ Committed"

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expiration_date = now_utc + datetime.timedelta(days=(req.days + bonus_days))
    expiration_date = expiration_date.replace(hour=23, minute=59, second=59)
    price_locked_until = (now_utc + datetime.timedelta(minutes=15)).isoformat()

    # CRITICAL FIX: Returning actual validated Pydantic Instance instead of raw dict
    return PriceResponse(
        tier=req.tier,
        days_selected=req.days,
        bonus_days=bonus_days,
        total_access_days=req.days + bonus_days,
        currency=currency,
        symbol=CURRENCY_SYMBOLS.get(currency, '$'),
        badge=badge,
        subtotal=round(subtotal_local, 2),
        discount_amount=round(discount_amount_local, 2),
        tax_amount=round(tax_amount, 2),
        gateway_fee=round(gateway_fee, 2),
        total_checkout_amount=round(total_charged, 2),
        expires_at=expiration_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
        price_locked_until=price_locked_until
    )
