import json
from typing import Dict, Any, Optional
import stripe
from app.core.config import settings


stripe.api_key = settings.STRIPE_API_KEY


def create_stripe_subscription(customer_id: str, price_id: str, metadata: Optional[dict] = None) -> Dict[str, Any]:
    if not settings.STRIPE_API_KEY:
        return {
            "status": "failed",
            "reason": "stripe_api_key_not_configured",
            "customer_id": customer_id,
            "price_id": price_id,
        }
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            metadata=metadata or {},
        )
        return {
            "status": "created",
            "provider": "stripe",
            "customer_id": customer_id,
            "price_id": price_id,
            "provider_payment_id": subscription.id,
            "stripe_response": subscription.to_dict(),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "reason": "stripe_error",
            "message": str(exc),
        }


def verify_stripe_webhook(payload: bytes, sig_header: str) -> dict:
    if not settings.STRIPE_WEBHOOK_SECRET:
        return json.loads(payload)
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return event.to_dict()
    except Exception as exc:
        raise ValueError(str(exc))


def initiate_mpesa_payment(phone_number: str, amount: float) -> Dict[str, Any]:
    if amount <= 0:
        return {"status": "failed", "reason": "invalid_amount", "amount": amount}
    return {
        "status": "queued",
        "provider": "mpesa",
        "phone_number": phone_number,
        "amount": amount,
        "message": "M-Pesa payment request queued as a placeholder.",
    }
