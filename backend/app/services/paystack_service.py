"""
VEKTRA Paystack Integration
============================
Handles payment initialization and verification for Africa.
Works with M-Pesa, card payments across Kenya/Nigeria/Ghana etc.
"""

import hashlib
import hmac
from typing import Optional

import httpx
from app.core.config import settings

PAYSTACK_BASE = "https://api.paystack.co"


def verify_webhook_signature(payload: bytes, signature: Optional[str], secret: Optional[str] = None) -> bool:
    """Verify Paystack webhook signature using HMAC-SHA512."""
    secret_value = (secret or settings.PAYSTACK_WEBHOOK_SECRET or "").strip()
    if not secret_value or not signature:
        return False

    expected = hmac.new(secret_value.encode("utf-8"), payload, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


def get_headers():
    if not settings.PAYSTACK_SECRET_KEY:
        raise ValueError("PAYSTACK_SECRET_KEY not configured. Please add it to your environment variables.")
    return {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

async def initialize_payment(
    email: str,
    amount_kobo: int,  # Amount in smallest currency unit (kobo/pesewas/cents)
    reference: str,
    metadata: dict = None,
    currency: str = "KES",
    callback_url: str = None,
) -> dict:
    """
    Initialize a Paystack payment.
    Returns authorization_url to redirect user to.
    """
    if amount_kobo <= 0:
        return {"status": False, "message": "Amount must be greater than zero."}

    try:
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "currency": currency,
            "metadata": metadata or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                json=payload,
                headers=get_headers(),
                timeout=30.0
            )
            response = res.json()
            if res.status_code >= 400:
                return {
                    "status": False,
                    "message": response.get("message") if isinstance(response, dict) else "Paystack request failed.",
                    "status_code": res.status_code,
                    "response": response,
                }
            return response
    except ValueError as exc:
        return {"status": False, "message": str(exc)}
    except httpx.HTTPError as exc:
        return {"status": False, "message": f"Paystack request failed: {str(exc)}"}

async def verify_payment(reference: str) -> dict:
    """Verify a payment by reference."""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{PAYSTACK_BASE}/transaction/verify/{reference}",
                headers=get_headers(),
                timeout=30.0
            )
            response = res.json()
            if res.status_code >= 400:
                return {
                    "status": False,
                    "message": response.get("message") if isinstance(response, dict) else "Verification failed.",
                    "status_code": res.status_code,
                    "response": response,
                }
            return response
    except ValueError as exc:
        return {"status": False, "message": str(exc)}
    except httpx.HTTPError as exc:
        return {"status": False, "message": f"Paystack verification failed: {str(exc)}"}
