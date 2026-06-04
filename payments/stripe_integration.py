"""Stripe integration — delegates to the shared payment service.

For the real Stripe SDK call (requires ``stripe`` package and a live API key),
use ``create_subscription_via_sdk`` directly.
"""
import stripe
from app.core.config import settings
from app.services.payment_service import create_stripe_subscription  # noqa: F401 – re-export

stripe.api_key = settings.STRIPE_API_KEY


def create_subscription_via_sdk(customer_id: str, price_id: str):
    """Create a Stripe subscription using the official SDK."""
    return stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
    )
