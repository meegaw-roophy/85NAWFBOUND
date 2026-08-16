from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
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
from app.services.payment_service import create_stripe_subscription, initiate_mpesa_payment
from app.services.paystack_service import initialize_payment as initialize_paystack_payment

router = APIRouter(tags=["payments"])


@router.get("", response_model=List[PaymentOut])
async def list_payments(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return await crud.list_payments(db, user_id)


@router.post("/stripe", response_model=PaymentOut)
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


@router.post("/paystack", response_model=PaymentOut)
async def paystack_payment(
    user_id: int,
    payload: PaystackPaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

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
            "tier": payload.tier or 'tier1'
            },
            currency=payload.currency or 'KES',
            callback_url=payload.callback_url,
        )

        # Update local payment with Paystack response
        status = result.get('status') or (result.get('data', {}).get('status') if isinstance(result, dict) else 'pending')
        provider_payment_id = None
        try:
            provider_payment_id = result.get('data', {}).get('reference')
        except Exception:
            provider_payment_id = None

        payment = await crud.update_payment_status(db, payment.id, status or 'pending', result, provider_payment_id=provider_payment_id)
        return payment
        
    except ValueError as e:
        # Configuration error (missing API key)
        raise HTTPException(status_code=500, detail=f"Payment provider not configured: {str(e)}")
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")


@router.post("/{payment_id}/status", response_model=PaymentOut)
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

@router.get("/payments/paystack/verify/{reference}")
async def verify_paystack(
    reference: str,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    from app.services.paystack_service import verify_payment
    result = await verify_payment(reference)
    
    if result.get('data', {}).get('status') == 'success':
        # Activate user tier based on metadata
        metadata = result.get('data', {}).get('metadata', {})
        # Update user tier
        current_user.tier = metadata.get('tier', 'tier1')
        db.add(current_user)
        await db.commit()
        return {"status": "success", "tier": current_user.tier}
    
    return {"status": "pending"}