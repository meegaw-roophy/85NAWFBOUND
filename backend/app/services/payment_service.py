from typing import Dict, Any
from app.core.config import settings


def create_stripe_subscription(customer_id: str, price_id: str) -> Dict[str, Any]:
    if not settings.STRIPE_API_KEY:
        return {
            "status": "failed",
            "reason": "stripe_api_key_not_configured",
            "customer_id": customer_id,
            "price_id": price_id,
        }
    return {
        "status": "success",
        "provider": "stripe",
        "customer_id": customer_id,
        "price_id": price_id,
        "message": "Stripe payment placeholder executed.",
    }


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
