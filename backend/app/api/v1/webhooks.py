from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.services.payment_service import verify_stripe_webhook
from app import crud

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
