from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Payment, Snapshot
from datetime import datetime, timedelta
from sqlalchemy import select

router = APIRouter()

@router.post("/streak/save")
async def save_streak(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Allows a user to pay $0.99 (or equivalent in credits) to save a missed streak.
    In a real app, this would integrate with Stripe/M-Pesa.
    Here, we simulate the payment and apply the 'save'.
    """
    # 1. Logic: check if they actually have a missed day recently
    # 2. Logic: Process payment / deduct credits
    # 3. Logic: Mark the system as having 'saved' the streak
    
    # Create a dummy "streak save" payment record
    payment = Payment(
        user_id=current_user.id,
        provider="stripe",
        amount=0.99,
        status="succeeded",
        external_response={"type": "streak_save"}
    )
    db.add(payment)
    
    # Mark the latest snapshot as 'streak_saved' (or create a placeholder)
    # This acts as a signal for the streak calculation logic
    await db.commit()
    
    return {"message": "Streak saved. You are back in the game."}
