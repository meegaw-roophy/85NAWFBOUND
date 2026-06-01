import stripe
from app.core.config import settings

stripe.api_key = settings.STRIPE_API_KEY

def create_subscription(customer_id: str, price_id: str):
    """Create a Stripe subscription placeholder."""
    # Implement real error handling and webhook handling in production.
    return stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
    )
