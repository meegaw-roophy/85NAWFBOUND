from fastapi import APIRouter, Depends
from typing import List
from app.schemas import (
    SubscriptionCreate,
    SubscriptionOut,
    StripePaymentRequest,
    MpesaPaymentRequest,
)
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import verify_owner
from app.services.payment_service import create_stripe_subscription, initiate_mpesa_payment

router = APIRouter()


@router.post("/users/{user_id}/subscriptions", response_model=SubscriptionOut)
async def upsert_subscription(
    user_id: int,
    payload: SubscriptionCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(verify_owner),
):
    subscription = await crud.create_or_update_subscription(db, user_id, payload.dict(exclude_none=True))
    return subscription


@router.get("/users/{user_id}/subscriptions", response_model=List[SubscriptionOut])
async def get_subscriptions(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(verify_owner)):
    subscriptions = await crud.list_subscriptions(db, user_id)
    return subscriptions


@router.post("/users/{user_id}/payments/stripe")
async def stripe_payment(
    user_id: int,
    payload: StripePaymentRequest,
    current_user=Depends(verify_owner),
):
    result = create_stripe_subscription(payload.customer_id or "", payload.price_id)
    return result


@router.post("/users/{user_id}/payments/mpesa")
async def mpesa_payment(
    user_id: int,
    payload: MpesaPaymentRequest,
    current_user=Depends(verify_owner),
):
    result = initiate_mpesa_payment(payload.phone_number, payload.amount)
    return result
