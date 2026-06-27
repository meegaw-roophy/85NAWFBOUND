from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas import (
    SubscriptionCreate,
    SubscriptionOut,
    StripePaymentRequest,
    MpesaPaymentRequest,
    PaymentOut,
    PaymentUpdate,
)
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user
from app.services.payment_service import create_stripe_subscription, initiate_mpesa_payment

router = APIRouter()


@router.post("/users/{user_id}/subscriptions", response_model=SubscriptionOut)
async def upsert_subscription(
    user_id: int,
    payload: SubscriptionCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    subscription = await crud.create_or_update_subscription(db, user_id, payload.dict(exclude_none=True))
    return subscription


@router.get("/users/{user_id}/subscriptions", response_model=List[SubscriptionOut])
async def get_subscriptions(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    subscriptions = await crud.list_subscriptions(db, user_id)
    return subscriptions


@router.get("/users/{user_id}/payments", response_model=List[PaymentOut])
async def list_payments(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return await crud.list_payments(db, user_id)


@router.post("/users/{user_id}/payments/stripe", response_model=PaymentOut)
async def stripe_payment(
    user_id: int,
    payload: StripePaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    payment = await crud.create_payment(db, user_id, {
        "provider": "stripe",
        "provider_customer_id": payload.customer_id,
        "amount": None,
        "currency": "usd",
        "status": "pending",
        "external_response": None,
    })
    result = create_stripe_subscription(payload.customer_id or "", payload.price_id, metadata={"local_payment_id": str(payment.id), "user_id": str(user_id)})
    payment = await crud.update_payment_status(
        db,
        payment.id,
        result.get("status", "pending"),
        result,
        provider_payment_id=result.get("provider_payment_id"),
    )
    return payment


@router.post("/users/{user_id}/payments/mpesa", response_model=PaymentOut)
async def mpesa_payment(
    user_id: int,
    payload: MpesaPaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result = initiate_mpesa_payment(payload.phone_number, payload.amount)
    payment = await crud.create_payment(db, user_id, {
        "provider": "mpesa",
        "provider_customer_id": payload.phone_number,
        "amount": payload.amount,
        "currency": "kes",
        "status": result.get("status", "unknown"),
        "external_response": result,
    })
    return payment


@router.post("/users/{user_id}/payments/{payment_id}/status", response_model=PaymentOut)
async def update_payment_status(
    user_id: int,
    payment_id: int,
    payload: PaymentUpdate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    payment = await crud.update_payment_status(db, payment_id, payload.status, payload.external_response)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
