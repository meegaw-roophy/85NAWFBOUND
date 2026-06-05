from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from pydantic import BaseModel
from app.schemas import (
    SubscriptionCreate,
    SubscriptionOut,
    StripePaymentRequest,
    MpesaPaymentRequest,
)
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user
from app.services.payment_service import (
    create_stripe_subscription,
    create_stripe_checkout_session,
    verify_stripe_webhook,
    initiate_mpesa_payment,
)

router = APIRouter()


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str = "http://localhost:8001/?payment=success"
    cancel_url: str = "http://localhost:8001/?payment=cancelled"


@router.post("/users/{user_id}/subscriptions", response_model=SubscriptionOut)
async def upsert_subscription(
    user_id: int,
    payload: SubscriptionCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    subscription = await crud.create_or_update_subscription(db, user_id, payload.model_dump(exclude_none=True))
    return subscription


@router.get("/users/{user_id}/subscriptions", response_model=List[SubscriptionOut])
async def get_subscriptions(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    subscriptions = await crud.list_subscriptions(db, user_id)
    return subscriptions


@router.post("/users/{user_id}/payments/stripe")
async def stripe_payment(
    user_id: int,
    payload: StripePaymentRequest,
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = create_stripe_subscription(payload.customer_id or "", payload.price_id)
    return result


@router.post("/users/{user_id}/payments/stripe/checkout")
async def stripe_checkout(
    user_id: int,
    payload: CheckoutRequest,
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = create_stripe_checkout_session(payload.price_id, payload.success_url, payload.cancel_url)
    if result["status"] == "failed":
        raise HTTPException(status_code=400, detail=result.get("reason", "Checkout failed"))
    return result


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    result = verify_stripe_webhook(payload, sig_header)
    if not result["verified"]:
        raise HTTPException(status_code=400, detail=result.get("reason", "Webhook verification failed"))
    # Process the event
    event = result["event"]
    event_type = event.get("type", "")
    # Handle subscription lifecycle events
    if event_type == "invoice.payment_succeeded":
        return {"status": "processed", "event": event_type}
    elif event_type == "customer.subscription.deleted":
        return {"status": "processed", "event": event_type}
    return {"status": "received", "event": event_type}


@router.post("/users/{user_id}/payments/mpesa")
async def mpesa_payment(
    user_id: int,
    payload: MpesaPaymentRequest,
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = initiate_mpesa_payment(payload.phone_number, payload.amount)
    return result
