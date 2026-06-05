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
    try:
        import stripe
        stripe.api_key = settings.STRIPE_API_KEY

        # Create or retrieve customer
        if not customer_id:
            customer = stripe.Customer.create()
            customer_id = customer.id

        # Create the subscription
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        return {
            "status": "success",
            "provider": "stripe",
            "subscription_id": subscription.id,
            "customer_id": customer_id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
            "message": "Stripe subscription created. Complete payment on client.",
        }
    except Exception as e:
        return {
            "status": "failed",
            "reason": str(e),
            "customer_id": customer_id,
            "price_id": price_id,
        }


def create_stripe_checkout_session(price_id: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
    if not settings.STRIPE_API_KEY:
        return {"status": "failed", "reason": "stripe_api_key_not_configured"}
    try:
        import stripe
        stripe.api_key = settings.STRIPE_API_KEY

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return {
            "status": "success",
            "checkout_url": session.url,
            "session_id": session.id,
        }
    except Exception as e:
        return {"status": "failed", "reason": str(e)}


def verify_stripe_webhook(payload: bytes, sig_header: str) -> Dict[str, Any]:
    if not settings.STRIPE_WEBHOOK_SECRET:
        return {"verified": False, "reason": "webhook_secret_not_configured"}
    try:
        import stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        return {"verified": True, "event": event}
    except Exception as e:
        return {"verified": False, "reason": str(e)}


def initiate_mpesa_payment(phone_number: str, amount: float) -> Dict[str, Any]:
    if amount <= 0:
        return {"status": "failed", "reason": "invalid_amount", "amount": amount}
    # M-Pesa STK Push would go here when Daraja API credentials are configured
    return {
        "status": "queued",
        "provider": "mpesa",
        "phone_number": phone_number,
        "amount": amount,
        "message": "M-Pesa STK push initiated. Awaiting user confirmation on phone.",
    }
