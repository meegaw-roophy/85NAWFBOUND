"""M-Pesa integration — delegates to the shared payment service.

The placeholder logic now lives in ``app.services.payment_service``.
Import from there for the canonical implementation.
"""
from app.services.payment_service import initiate_mpesa_payment  # noqa: F401 – re-export


def initiate_stk_push(phone_number: str, amount: float):
    """Convenience alias kept for backward compatibility."""
    return initiate_mpesa_payment(phone_number, amount)
