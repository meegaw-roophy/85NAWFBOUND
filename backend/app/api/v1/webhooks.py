from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User, Subscription, Payment
from app.services.payment_service import verify_stripe_webhook
from app.services.paystack_service import verify_webhook_signature
from app import crud
from datetime import datetime, timedelta
from app.core.config import settings

router = APIRouter()


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: AsyncSession = Depends(get_session),
):
    body = await request.body()
    try:
        event = verify_stripe_webhook(body, stripe_signature)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})
    metadata = data_object.get("metadata", {}) if isinstance(data_object, dict) else {}
    local_payment_id = metadata.get("local_payment_id")

    if not local_payment_id:
        return {"received": True, "message": "Stripe webhook received without local_payment_id metadata."}

    status_value = "updated"
    if event_type in ["invoice.payment_succeeded", "payment_intent.succeeded"]:
        status_value = "succeeded"
    elif event_type in ["invoice.payment_failed", "payment_intent.payment_failed"]:
        status_value = "failed"
    elif event_type == "customer.subscription.created":
        status_value = "created"

    payment = await crud.update_payment_status(
        db,
        int(local_payment_id),
        status_value,
        event,
        provider_payment_id=data_object.get("id") if isinstance(data_object, dict) else None,
    )

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local payment record not found")

    return {"received": True, "event_type": event_type, "payment_id": local_payment_id}


@router.post("/webhooks/mpesa")
async def mpesa_webhook(payload: dict, db: AsyncSession = Depends(get_session)):
    payment_id = payload.get("payment_id")
    status_value = payload.get("status")
    if not payment_id or not status_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="payment_id and status are required")

    payment = await crud.update_payment_status(db, int(payment_id), status_value, payload)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    return {"received": True, "payment_id": payment_id, "status": status_value}


@router.post("/webhooks/paystack")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: AsyncSession = Depends(get_session),
):
    """Handle Paystack webhook events for subscription management"""
    body = await request.body()
    if not verify_webhook_signature(body, x_paystack_signature, settings.PAYSTACK_WEBHOOK_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Paystack signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event = payload.get("event")
    data = payload.get("data", {})

    if event == "charge.success":
        reference = data.get("reference")
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
        user_id = metadata.get("user_id")
        tier = metadata.get("tier", "tier1")

        if reference:
            payment_result = await db.execute(
                select(Payment).where(Payment.provider_payment_id == reference)
            )
            payment = payment_result.scalar_one_or_none()
            if payment:
                payment.status = "succeeded"
                payment.external_response = payload
                db.add(payment)
                await db.commit()

        if user_id:
            user_result = await db.execute(select(User).where(User.id == int(user_id)))
            user = user_result.scalar_one_or_none()
            if user:
                user.tier = tier
                db.add(user)
                await db.commit()

            subscription_result = await db.execute(
                select(Subscription).where(Subscription.user_id == int(user_id)).order_by(Subscription.created_at.desc())
            )
            subscription = subscription_result.scalar_one_or_none()
            if subscription:
                subscription.active = True
                subscription.provider_subscription_id = reference
                subscription.last_webhook_at = datetime.utcnow()
                subscription.expires_at = (subscription.expires_at or datetime.utcnow()) + timedelta(days=subscription.duration_days or 30)
                db.add(subscription)
                await db.commit()

    elif event == "subscription.disable":
        reference = data.get("subscription_code")
        result = await db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_id == reference
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.active = False
            subscription.last_webhook_at = datetime.utcnow()
            db.add(subscription)
            await db.commit()

    elif event == "subscription.not_renew":
        reference = data.get("subscription_code")
        result = await db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_id == reference
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.auto_renew = False
            subscription.last_webhook_at = datetime.utcnow()
            db.add(subscription)
            await db.commit()

    return {"received": True, "event": event}


async def check_and_renew_subscriptions(db: AsyncSession):
    """Check for expired subscriptions with auto-renew enabled and renew them"""
    now = datetime.utcnow()
    
    # Find subscriptions that are expiring within 24 hours and have auto_renew enabled
    result = await db.execute(
        select(Subscription).where(
            Subscription.active == True,
            Subscription.auto_renew == True,
            Subscription.expires_at <= now + timedelta(hours=24),
            Subscription.expires_at > now
        )
    )
    subscriptions = result.scalars().all()
    
    for sub in subscriptions:
        # TODO: Implement actual renewal logic with Paystack API
        # For now, just extend the subscription by the original duration
        if sub.duration_days:
            sub.expires_at = sub.expires_at + timedelta(days=sub.duration_days)
            sub.last_webhook_at = now
            db.add(sub)
    
    await db.commit()
    return len(subscriptions)
