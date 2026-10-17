"""
Subscription API
Handles subscription plans, payments, and user subscription status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime

from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User, Subscription, Payment
from app.schemas import SubscriptionCreate, SubscriptionOut, PaymentOut
from app.api.v1.pricing import paid_access_for_payment, tier_catalog

# Plan id -> tier name granted on User.tier once a payment for that plan clears.
PLAN_TO_TIER = {
    "free": "free",
    "tier1": "tier1",
    "tier2": "tier2",
    "tier3": "tier3",
}

router = APIRouter()


@router.get("/current", response_model=SubscriptionOut)
async def get_current_subscription(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's current active subscription"""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.active == True)
        .order_by(Subscription.created_at.desc())
    )
    subscription = result.scalars().first()

    if not subscription:
        # Transient, never-persisted object purely so from_attributes=True
        # serializes it the same way as a real one - hand-building a dict
        # here is exactly how this endpoint ended up missing SubscriptionOut's
        # required user_id/provider fields and 500ing for every free user.
        subscription = Subscription(
            id=0,
            user_id=current_user.id,
            provider="none",
            plan="free",
            active=True,
        )
        subscription.days_remaining = None
        return subscription

    subscription.days_remaining = None
    if subscription.expires_at:
        subscription.days_remaining = (subscription.expires_at - datetime.utcnow()).days

    return subscription


@router.post("/create", response_model=SubscriptionOut)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new subscription — only once a real payment has cleared.

    This never trusts client-supplied amount/plan on its own: it requires a
    Payment row that belongs to this user and is already marked 'succeeded'
    (set by a verified webhook, e.g. Paystack's charge.success handler).
    Without that check, anyone could call this endpoint directly and grant
    themselves any paid tier for free.
    """
    payment_result = await db.execute(
        select(Payment).where(
            Payment.id == subscription_data.payment_id,
            Payment.user_id == current_user.id,
        )
    )
    payment = payment_result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail="Payment has not succeeded yet")

    # Plan and duration come from what the provider confirmed was charged,
    # never from the request body: the client used to send a fixed 30 days
    # (so longer purchases were shortchanged) and any plan it liked.
    access = paid_access_for_payment(payment, current_user.country_code)
    if access is None:
        raise HTTPException(status_code=400, detail="Payment amount does not cover this plan")

    # Deactivate existing subscriptions
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.active == True)
    )
    existing = result.scalars().all()
    for sub in existing:
        sub.active = False

    # Expiry is anchored to when the payment cleared, so re-submitting the
    # same payment_id reproduces the same window instead of extending it.
    duration_days = access.days
    expires_at = access.expires_at

    subscription = Subscription(
        user_id=current_user.id,
        provider=payment.provider,
        plan=access.tier,
        duration_days=duration_days,
        discount_pct=subscription_data.discount_pct,
        amount_paid=access.amount,
        currency=access.currency,
        active=True,
        starts_at=payment.succeeded_at or datetime.utcnow(),
        expires_at=expires_at
    )

    db.add(subscription)

    current_user.tier = PLAN_TO_TIER[access.tier]
    current_user.tier_expires_at = expires_at
    db.add(current_user)

    await db.commit()
    await db.refresh(subscription)

    # Same fix as /current: return the real ORM object (from_attributes=True
    # picks up every column automatically) instead of a hand-built dict that
    # can silently miss required schema fields. This endpoint fires right
    # after a real payment clears - it was 500ing here even though the
    # subscription/tier had already been saved correctly, meaning a paying
    # customer would see an error immediately after a successful payment.
    subscription.days_remaining = max(0, (expires_at - datetime.utcnow()).days)
    return subscription


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    plans = [
        {
            "id": tier["id"],
            "name": tier["name"],
            "price": float(tier["price_usd"]),
            "currency": "USD",
            "duration_days": None if tier["id"] == "free" else 30,
            "features": tier["features"],
        }
        for tier in tier_catalog()
    ]
    return {"plans": plans}


@router.get("/payments", response_model=List[PaymentOut])
async def get_payment_history(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get user's payment history"""
    result = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(20)
    )
    payments = result.scalars().all()
    
    return [
        {
            "id": p.id,
            "provider": p.provider,
            "amount": p.amount,
            "currency": p.currency,
            "status": p.status,
            "created_at": p.created_at
        }
        for p in payments
    ]


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update subscription settings (e.g., auto_renew)"""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id
        )
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Update auto_renew if provided
    if 'auto_renew' in payload:
        subscription.auto_renew = payload['auto_renew']
    
    # Update webhook settings if provided
    if 'webhook_url' in payload:
        subscription.webhook_url = payload['webhook_url']
    if 'webhook_secret' in payload:
        subscription.webhook_secret = payload['webhook_secret']
    
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "id": subscription.id,
        "auto_renew": subscription.auto_renew,
        "webhook_url": subscription.webhook_url
    }
