"""
VEKTRA Paystack Integration
============================
Handles payment initialization and verification for Africa.
Works with M-Pesa, card payments across Kenya/Nigeria/Ghana etc.
"""

import httpx
from app.core.config import settings

PAYSTACK_BASE = "https://api.paystack.co"

def get_headers():
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
        return res.json()

async def verify_payment(reference: str) -> dict:
    """Verify a payment by reference."""
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{PAYSTACK_BASE}/transaction/verify/{reference}",
            headers=get_headers(),
            timeout=30.0
        )
        return res.json()