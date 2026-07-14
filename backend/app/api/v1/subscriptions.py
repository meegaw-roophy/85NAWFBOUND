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
    """Create a new subscription"""
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
    
    # Create new subscription
    subscription = Subscription(
        user_id=current_user.id,
        provider=subscription_data.provider or "stripe",
        plan=subscription_data.plan,
        duration_days=duration_days,
        discount_pct=subscription_data.discount_pct,
        amount_paid=subscription_data.amount_paid,
        currency=subscription_data.currency or "USD",
        active=True,
        starts_at=datetime.utcnow(),
        expires_at=expires_at
    )
    
    db.add(subscription)
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
            "price": 9.99,
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
            "price": 19.99,
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
