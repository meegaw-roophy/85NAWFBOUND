import logging
import stripe
from app.core.config import settings

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_API_KEY


def create_subscription(customer_id: str, price_id: str):
    """Create a Stripe subscription."""
    if not settings.STRIPE_API_KEY:
        raise ValueError("STRIPE_API_KEY is not configured")

    try:
        return stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
        )
    except stripe.error.CardError as exc:
        logger.warning("Stripe card error for customer %s: %s", customer_id, exc)
        raise
    except stripe.error.InvalidRequestError as exc:
        logger.error("Stripe invalid request (customer=%s, price=%s): %s", customer_id, price_id, exc)
        raise
    except stripe.error.AuthenticationError as exc:
        logger.error("Stripe authentication failed: %s", exc)
        raise
    except stripe.error.StripeError as exc:
        logger.error("Stripe API error: %s", exc)
        raise
