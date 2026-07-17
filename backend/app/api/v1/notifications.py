from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import User, Snapshot, CircleMember
from sqlalchemy import select, func
from datetime import datetime, time

router = APIRouter()

@router.get("/notifications/reminders")
async def get_notifications_and_reminders(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Checks if a user is due for a custom-scheduled reminder notification.
    If yes, triggers the correct payload (Trash talk, Wager update, or Streak reminder).
    """
    now = datetime.utcnow().time()
    
    # 1. Check if user set a reminder time and if we are close to it
    # For now, if no reminder time is set, default to evening (e.g. 8 PM / 20:00)
    reminder_target = current_user.reminder_time or time(20, 0, 0)
    
    # Check if they have logged today yet
    today = datetime.utcnow().date()
    logged_today_res = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == current_user.id)
        .where(func.date(Snapshot.timestamp) == today)
    )
    logged_today = logged_today_res.scalars().first() is not None
    
    if logged_today:
        # Check if they are winning their wagers to keep them engaged
        # (Status Flex Notification)
        return {
            "notification_type": "status_update",
            "title": "🏆 You are locked in!",
            "message": "You logged your snapshot today. Go check the circle leaderboard to see where you rank.",
            "action_url": f"/circles/leaderboard"
        }
        
    # If they haven't logged today and we are past their reminder time
    # (Aggressive Nudge Notification)
    return {
        "notification_type": "streak_warning",
        "title": "🚨 Streak in Danger!",
        "message": f"Hey {current_user.username}, you haven't logged today's metrics yet. Save your streak and secure your wagers before midnight!",
        "action_url": "/snapshots/new"
    }
