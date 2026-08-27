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
    # Disabled: this accepted an unauthenticated {payment_id, status} body and
    # would mark ANY payment record "succeeded" with no signature check and no
    # real Safaricom Daraja integration behind it (initiate_mpesa_payment is
    # still a placeholder). Re-enable only once M-Pesa is actually wired up
    # with Daraja callback validation.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="M-Pesa is not yet available.")


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
        special_offer = str(metadata.get("special_offer", "false")).lower() == "true"
        offer_expires_at = datetime.fromisoformat(
            metadata["access_expires_at"].replace("Z", "+00:00")
        ) if special_offer and metadata.get("access_expires_at") else None

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
                user.tier_expires_at = offer_expires_at or user.tier_expires_at
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
                subscription.expires_at = offer_expires_at or (
                    subscription.expires_at or datetime.utcnow()
                ) + timedelta(days=subscription.duration_days or 30)
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
    from app.services.paystack_service import initialize_payment
    from app import crud
    
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
    
    renewed_count = 0
    for sub in subscriptions:
        try:
            # Get user for this subscription
            user_result = await db.execute(select(User).where(User.id == sub.user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                continue
            
            # Calculate renewal amount (use original amount or default)
            renewal_amount = sub.amount_paid or 1000  # Default to 1000 if no amount stored
            amount_kobo = int(renewal_amount * 100)
            
            # Create a new payment record for renewal
            payment = await crud.create_payment(db, sub.user_id, {
                "provider": "paystack",
                "provider_customer_id": user.email,
                "amount": renewal_amount,
                "currency": sub.currency or "KES",
                "status": "pending",
                "external_response": None,
            })
            
            # Initialize Paystack payment for renewal
            reference = f"renew_{payment.id}_{sub.id}"
            paystack_result = await initialize_payment(
                email=user.email,
                amount_kobo=amount_kobo,
                reference=reference,
                metadata={
                    "local_payment_id": str(payment.id),
                    "user_id": str(sub.user_id),
                    "tier": sub.plan or "tier1",
                    "subscription_id": str(sub.id),
                    "renewal": "true"
                },
                currency=sub.currency or "KES",
                callback_url=None  # No callback for auto-renewal
            )
            
            # Update payment with Paystack response
            if paystack_result.get("status") is False:
                payment.status = "failed"
                payment.external_response = paystack_result
            else:
                provider_payment_id = paystack_result.get('data', {}).get('reference')
                payment.provider_payment_id = provider_payment_id
                payment.external_response = paystack_result
                
                # Store payment URL for user to complete
                auth_url = paystack_result.get('data', {}).get('authorization_url')
                if auth_url:
                    # Store in subscription metadata for user access
                    sub.renewal_payment_url = auth_url
                    sub.renewal_payment_id = str(payment.id)
                    sub.renewal_expires_at = sub.expires_at + timedelta(days=7)  # Give 7 days to pay
            
            db.add(payment)
            db.add(sub)
            renewed_count += 1
            
        except Exception as e:
            # Log error but continue with other subscriptions
            print(f"Auto-renewal failed for subscription {sub.id}: {str(e)}")
            continue
    
    await db.commit()
    return renewed_count
