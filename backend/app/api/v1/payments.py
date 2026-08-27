from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from typing import List
from sqlalchemy import select
from app.schemas import (
    SubscriptionCreate,
    SubscriptionOut,
    StripePaymentRequest,
    MpesaPaymentRequest,
    PaystackPaymentRequest,
    PaymentOut,
    PaymentUpdate,
)
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user
from app.db.models import Payment
from app.services.payment_service import create_stripe_subscription, initiate_mpesa_payment
from app.services.paystack_service import initialize_payment as initialize_paystack_payment

router = APIRouter(tags=["payments"])


@router.get("", response_model=List[PaymentOut])
async def list_payments(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return await crud.list_payments(db, user_id)


@router.post("/stripe", response_model=PaymentOut)
async def stripe_payment(
    user_id: int,
    payload: StripePaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not allowed")
    payment = await crud.create_payment(db, user_id, {
        "provider": "stripe",
        "provider_customer_id": payload.customer_id,
        "amount": None,
        "currency": "usd",
        "status": "pending",
        "external_response": None,
    })
    result = create_stripe_subscription(payload.customer_id or "", payload.price_id, metadata={"local_payment_id": str(payment.id), "user_id": str(user_id), "tier": payload.tier or 'tier1'},)
    payment = await crud.update_payment_status(
        db,
        payment.id,
        result.get("status", "pending"),
        result,
        provider_payment_id=result.get("provider_payment_id"),
    )
    return payment


@router.post("/mpesa", response_model=PaymentOut)
async def mpesa_payment(
    user_id: int,
    payload: MpesaPaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not allowed")
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


@router.post("/paystack", response_model=PaymentOut)
async def paystack_payment(
    user_id: int,
    payload: PaystackPaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not allowed")

    try:
        # Create local pending payment record
        payment = await crud.create_payment(db, user_id, {
            "provider": "paystack",
            "provider_customer_id": payload.email,
            "amount": payload.amount,
            "currency": (payload.currency or 'KES').lower(),
            "status": "pending",
            "external_response": None,
        })

        # Initialize Paystack transaction
        result = await initialize_paystack_payment(
            email=payload.email,
            amount_kobo=int(payload.amount * 100),
            reference=str(payment.id),
            metadata={
                "local_payment_id": str(payment.id), 
                "user_id": str(user_id),
                "tier": payload.tier or 'tier1',
                "special_offer": bool(payload.special_offer),
                "access_expires_at": "2027-01-01T23:59:59+03:00" if payload.special_offer else None,
            },
            currency=payload.currency or 'KES',
            callback_url=payload.callback_url,
        )

        if result.get("status") is False:
            payment = await crud.update_payment_status(db, payment.id, "failed", result)
            raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=result.get("message") or "Paystack initialization failed")

        # FIX: Renamed 'status' variable to 'paystack_status' to bypass FastAPI namespace shadowing error
        raw_status = result.get('status')
        if isinstance(raw_status, bool):
            paystack_status = 'success' if raw_status else 'pending'
        elif isinstance(raw_status, str):
            paystack_status = raw_status.lower()
        else:
            paystack_status = 'pending'
            
        provider_payment_id = None
        try:
            provider_payment_id = result.get('data', {}).get('reference')
        except Exception:
            provider_payment_id = None

        payment = await crud.update_payment_status(db, payment.id, paystack_status, result, provider_payment_id=provider_payment_id)
        return payment
        
    except ValueError as e:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=f"Payment provider not configured: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=http_status.HTTP_502_BAD_GATEWAY, detail=f"Payment initialization failed: {str(e)}")


@router.post("/{payment_id}/status", response_model=PaymentOut)
async def update_payment_status(
    user_id: int,
    payment_id: int,
    payload: PaymentUpdate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not allowed")
    payment = await crud.update_payment_status(db, payment_id, payload.status, payload.external_response)
    if not payment:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment


@router.get("/paystack/verify/{reference}")
async def verify_paystack(
    reference: str,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Called by the frontend when Paystack redirects back after checkout.

    Confirms the charge directly with Paystack's servers (never trusts the
    redirect alone — that's just a browser navigation anyone could fake),
    then marks our local Payment row 'succeeded' so /subscriptions/create
    will accept it and actually activate the subscription.
    """
    from app.services.paystack_service import verify_payment
    result = await verify_payment(reference)

    if result.get('data', {}).get('status') == 'success':
        metadata = result.get('data', {}).get('metadata', {})
        tier = metadata.get('tier', 'tier1')

        try:
            payment_id = int(reference)
        except (TypeError, ValueError):
            payment_id = None

        payment = None
        if payment_id is not None:
            payment_result = await db.execute(
                select(Payment).where(Payment.id == payment_id, Payment.user_id == current_user.id)
            )
            payment = payment_result.scalar_one_or_none()

        if not payment:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Payment record not found")

        payment.status = "succeeded"
        payment.external_response = result
        db.add(payment)
        await db.commit()

        return {"status": "success", "tier": tier, "payment_id": payment.id}

    return {"status": "pending"}
