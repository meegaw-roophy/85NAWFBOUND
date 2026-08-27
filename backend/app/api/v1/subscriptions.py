"""
Subscription API
Handles subscription plans, payments, and user subscription status.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime, timedelta

from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User, Subscription, Payment
from app.schemas import SubscriptionCreate, SubscriptionOut, PaymentOut

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
        return {
            "id": 0,
            "plan": "free",
            "active": True,
            "expires_at": None,
            "days_remaining": None
        }
    
    days_remaining = None
    if subscription.expires_at:
        days_remaining = (subscription.expires_at - datetime.utcnow()).days
    
    return {
        "id": subscription.id,
        "plan": subscription.plan or "free",
        "active": subscription.active,
        "expires_at": subscription.expires_at,
        "days_remaining": days_remaining
    }


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

    # Deactivate existing subscriptions
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .where(Subscription.active == True)
    )
    existing = result.scalars().all()
    for sub in existing:
        sub.active = False

    # Calculate expiration
    duration_days = subscription_data.duration_days or 30
    expires_at = datetime.utcnow() + timedelta(days=duration_days)

    # Create new subscription, trusting the verified payment's own amount/
    # currency/provider rather than whatever the client claims.
    subscription = Subscription(
        user_id=current_user.id,
        provider=payment.provider,
        plan=subscription_data.plan,
        duration_days=duration_days,
        discount_pct=subscription_data.discount_pct,
        amount_paid=payment.amount,
        currency=payment.currency or "USD",
        active=True,
        starts_at=datetime.utcnow(),
        expires_at=expires_at
    )

    db.add(subscription)

    tier = PLAN_TO_TIER.get(subscription_data.plan, subscription_data.plan)
    if tier:
        current_user.tier = tier
        current_user.tier_expires_at = expires_at
        db.add(current_user)

    await db.commit()
    await db.refresh(subscription)

    return {
        "id": subscription.id,
        "plan": subscription.plan,
        "active": subscription.active,
        "expires_at": subscription.expires_at,
        "days_remaining": duration_days
    }


@router.get("/plans")
async def get_subscription_plans():
    """Get available subscription plans"""
    plans = [
        {
            "id": "free",
            "name": "Free",
            "price": 0,
            "currency": "USD",
            "duration_days": None,
            "features": [
                "Daily logging",
                "Basic VEKTRA score",
                "Weekly reports",
                "Limited analytics (7 days)"
            ]
        },
        {
            "id": "tier1",
            "name": "Pro",
            "price": 20.00,
            "currency": "USD",
            "duration_days": 30,
            "features": [
                "Everything in Free",
                "Advanced analytics (90 days)",
                "Goal prediction",
                "AI-powered reports",
                "Weekly comparison",
                "Priority support"
            ]
        },
        {
            "id": "tier2",
            "name": "Premium",
            "price": 50.00,
            "currency": "USD",
            "duration_days": 30,
            "features": [
                "Everything in Pro",
                "Unlimited analytics (1 year)",
                "Monthly reports",
                "Data export (CSV/PDF)",
                "Achievement tracking",
                "Streak calendar",
                "Dedicated support"
            ]
        },
        {
            "id": "tier3",
            "name": "Enterprise",
            "price": 49.99,
            "currency": "USD",
            "duration_days": 30,
            "features": [
                "Everything in Premium",
                "Team collaboration",
                "API access",
                "Custom integrations",
                "White-label reports",
                "Account manager"
            ]
        }
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
