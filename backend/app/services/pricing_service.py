"""
VEKTRA Pricing Service
======================
Handles location-based pricing using PPP (Purchasing Power Parity).
Adjusts subscription costs from $5-$30 based on user's location.
"""

from typing import Optional, Dict, Any

# PPP multipliers relative to USD (lower = cheaper cost of living)
# Source: World Bank PPP conversion factors
PPP_MULTIPLIERS = {
    # North America & Western Europe (high PPP - full price)
    'united states': 1.0,
    'usa': 1.0,
    'canada': 0.95,
    'united kingdom': 0.9,
    'uk': 0.9,
    'germany': 0.85,
    'france': 0.85,
    'netherlands': 0.85,
    'switzerland': 1.1,
    'norway': 1.0,
    'sweden': 0.9,
    'denmark': 0.95,
    
    # Eastern Europe (medium PPP)
    'poland': 0.6,
    'czech republic': 0.6,
    'hungary': 0.55,
    'romania': 0.5,
    'russia': 0.45,
    'ukraine': 0.35,
    
    # Asia (varied PPP)
    'japan': 0.85,
    'south korea': 0.75,
    'singapore': 0.8,
    'hong kong': 0.8,
    'china': 0.5,
    'india': 0.25,
    'indonesia': 0.3,
    'thailand': 0.4,
    'vietnam': 0.35,
    'philippines': 0.35,
    'malaysia': 0.45,
    
    # Africa (low PPP - discounted pricing)
    'kenya': 0.3,
    'nigeria': 0.3,
    'south africa': 0.5,
    'egypt': 0.3,
    'morocco': 0.4,
    'ghana': 0.35,
    'ethiopia': 0.25,
    'tanzania': 0.3,
    'uganda': 0.3,
    
    # South America (medium-low PPP)
    'brazil': 0.5,
    'argentina': 0.4,
    'chile': 0.55,
    'colombia': 0.4,
    'peru': 0.4,
    'mexico': 0.5,
    
    # Middle East
    'united arab emirates': 0.8,
    'uae': 0.8,
    'saudi arabia': 0.7,
    'israel': 0.85,
    'turkey': 0.45,
    
    # Oceania
    'australia': 0.9,
    'new zealand': 0.85,
}

# Base subscription tiers (USD)
BASE_PRICES = {
    'tier1': {
        'monthly': 5.0,
        'quarterly': 12.0,
        'annual': 40.0,
    },
    'tier2': {
        'monthly': 10.0,
        'quarterly': 25.0,
        'annual': 80.0,
    },
    'tier3': {
        'monthly': 20.0,
        'quarterly': 50.0,
        'annual': 160.0,
    },
}


class PricingService:
    """Handles location-based pricing calculations."""
    
    def extract_country_from_location(self, location: Optional[str]) -> Optional[str]:
        """
        Extract country name from location string.
        Returns lowercase country name or None.
        """
        if not location:
            return None
        
        location_lower = location.lower()
        
        # Check for known countries in the location string
        for country in PPP_MULTIPLIERS.keys():
            if country in location_lower:
                return country
        
        # Try to extract from common patterns like "Nairobi, Kenya" or "Kenya, Nairobi"
        parts = [p.strip().lower() for p in location.split(',')]
        for part in parts:
            if part in PPP_MULTIPLIERS:
                return part
        
        return None
    
    def get_ppp_multiplier(self, location: Optional[str]) -> float:
        """
        Get PPP multiplier for a location.
        Defaults to 1.0 (full price) if location not found.
        """
        country = self.extract_country_from_location(location)
        if country:
            return PPP_MULTIPLIERS.get(country, 1.0)
        return 1.0
    
    def calculate_price(
        self,
        base_price: float,
        location: Optional[str] = None,
        min_price: float = 5.0,
        max_price: float = 30.0
    ) -> Dict[str, Any]:
        """
        Calculate adjusted price based on location PPP.
        Ensures price stays within min-max bounds.
        
        Returns dict with:
        - original_price: base price in USD
        - adjusted_price: PPP-adjusted price
        - currency: USD (for now)
        - discount_pct: percentage discount from base
        - location: detected country
        - ppp_multiplier: the multiplier used
        """
        ppp_multiplier = self.get_ppp_multiplier(location)
        adjusted_price = base_price * ppp_multiplier
        
        # Ensure price stays within bounds
        adjusted_price = max(min_price, min(max_price, adjusted_price))
        
        discount_pct = ((base_price - adjusted_price) / base_price) * 100 if base_price > adjusted_price else 0
        
        country = self.extract_country_from_location(location)
        
        return {
            'original_price': base_price,
            'adjusted_price': round(adjusted_price, 2),
            'currency': 'USD',
            'discount_pct': round(discount_pct, 1),
            'location': country or 'Unknown',
            'ppp_multiplier': ppp_multiplier,
        }
    
    def get_subscription_price(
        self,
        tier: str = 'tier1',
        duration: str = 'monthly',
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get subscription price for a specific tier and duration.
        
        Args:
            tier: 'tier1', 'tier2', or 'tier3'
            duration: 'monthly', 'quarterly', or 'annual'
            location: user's location string
        """
        if tier not in BASE_PRICES:
            tier = 'tier1'
        if duration not in BASE_PRICES[tier]:
            duration = 'monthly'
        
        base_price = BASE_PRICES[tier][duration]
        return self.calculate_price(base_price, location)
    
    def get_all_tier_prices(self, location: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all available tier prices for a location.
        Useful for displaying pricing options to users.
        """
        prices = {}
        
        for tier in BASE_PRICES:
            prices[tier] = {}
            for duration in BASE_PRICES[tier]:
                prices[tier][duration] = self.get_subscription_price(tier, duration, location)
        
        return {
            'location': self.extract_country_from_location(location) or 'Unknown',
            'prices': prices,
        }


pricing_service = PricingService()
