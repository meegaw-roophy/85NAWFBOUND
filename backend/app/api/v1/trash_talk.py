from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import User, Snapshot
from sqlalchemy import select
from datetime import datetime

router = APIRouter()

TRASH_TALK_MESSAGES = [
    "Your VEKTRA score is lower than your potential. Are you sleeping or quitting?",
    "A lazy day? That wager pot won't win itself. Get back to work.",
    "Your focus is currently in the gutter. Your future self is disappointed.",
    "Do you want the prize, or do you want to keep making excuses?",
    "Zero logs today? That’s not a streak—that’s a surrender."
]

@router.post("/trash-talk/trigger")
async def trigger_trash_talk(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Triggers an AI-style 'trash talk' notification if the user is behind on their goals.
    """
    # Logic: Only trigger if score is < 50
    # In a real system, this would push to a notification service (Firebase/APNS)
    
    # Simulate finding their latest status
    result = await db.execute(select(Snapshot).where(Snapshot.user_id == current_user.id).order_by(Snapshot.timestamp.desc()).limit(1))
    latest = result.scalars().first()
    
    if latest and (latest.vektra_score or 100) < 50:
        import random
        msg = random.choice(TRASH_TALK_MESSAGES)
        
        # Log this incident
        latest.trash_talk_count += 1
        latest.last_trash_talk_sent = datetime.utcnow()
        await db.commit()
        
        return {"message": msg, "delivered": True}
        
    return {"message": "You're doing fine. No trash talk today.", "delivered": False}
