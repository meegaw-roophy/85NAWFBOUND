from fastapi import APIRouter, Query
from typing import Optional
from app.services.pricing_service import pricing_service

router = APIRouter()


@router.get("/pricing/subscription")
async def get_subscription_price(
    tier: str = Query("tier1", description="Subscription tier: tier1, tier2, tier3"),
    duration: str = Query("monthly", description="Duration: monthly, quarterly, annual"),
    location: Optional[str] = Query(None, description="User's location for PPP-based pricing")
):
    """
    Get subscription price for a specific tier and duration.
    Price is adjusted based on location using PPP (Purchasing Power Parity).
    """
    return pricing_service.get_subscription_price(tier, duration, location)


@router.get("/pricing/all-tiers")
async def get_all_tier_prices(
    location: Optional[str] = Query(None, description="User's location for PPP-based pricing")
):
    """
    Get all available subscription tier prices for a location.
    Returns pricing for all tiers and durations.
    """
    return pricing_service.get_all_tier_prices(location)


@router.get("/pricing/calculate")
async def calculate_custom_price(
    base_price: float = Query(..., description="Base price in USD"),
    location: Optional[str] = Query(None, description="User's location for PPP-based pricing"),
    min_price: float = Query(5.0, description="Minimum price floor"),
    max_price: float = Query(30.0, description="Maximum price ceiling")
):
    """
    Calculate PPP-adjusted price for a custom base price.
    Useful for one-time purchases or custom pricing.
    """
    return pricing_service.calculate_price(base_price, location, min_price, max_price)
