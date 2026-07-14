"""
Achievement API
Handles user achievements, badges, and gamification.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User
from app.schemas import AchievementOut
from app import crud

router = APIRouter()


@router.get("", response_model=List[AchievementOut])
async def get_achievements(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all achievements for the current user"""
    achievements = await crud.list_achievements(db, current_user.id)
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "achievement_id": a.achievement_id,
            "title": a.title,
            "description": a.description,
            "icon": a.icon,
            "rarity": a.rarity,
            "progress": a.progress,
            "completed": a.completed,
            "completed_at": a.completed_at,
            "created_at": a.created_at
        }
        for a in achievements
    ]


@router.get("/available")
async def get_available_achievements(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all available achievements with completion status"""
    user_achievements = await crud.list_achievements(db, current_user.id)
    completed_ids = {a.achievement_id for a in user_achievements if a.completed}
    
    available = []
    for achievement_id, definition in crud.ACHIEVEMENT_DEFINITIONS.items():
        available.append({
            "achievement_id": achievement_id,
            "title": definition['title'],
            "description": definition['description'],
            "icon": definition['icon'],
            "rarity": definition['rarity'],
            "completed": achievement_id in completed_ids
        })
    
    return {"achievements": available}


@router.post("/check")
async def check_achievements(
    snapshot_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Check for new achievements based on a snapshot"""
    from app.db.models import Snapshot
    
    # Get the snapshot
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.id == snapshot_id)
        .where(Snapshot.user_id == current_user.id)
    )
    snapshot = result.scalars().first()
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    # Check for new achievements
    new_achievements = await crud.check_and_unlock_achievements(db, current_user.id, snapshot)
    
    return {
        "new_achievements": [
            {
                "id": a.id,
                "achievement_id": a.achievement_id,
                "title": a.title,
                "icon": a.icon,
                "rarity": a.rarity
            }
            for a in new_achievements
        ]
    }


@router.get("/streak-calendar")
async def get_streak_calendar(
    days: int = 365,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get GitHub-style streak calendar data"""
    calendar_data = await crud.get_streak_calendar(db, current_user.id, days)
    return calendar_data


@router.get("/financial-health")
async def get_financial_health(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive financial health metrics"""
    financial_data = await crud.calculate_financial_health(db, current_user.id)
    return financial_data


@router.get("/monthly-replay")
async def get_monthly_replay(
    year: int = None,
    month: int = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get monthly replay data for historical review"""
    replay_data = await crud.get_monthly_replay(db, current_user.id, year, month)
    return replay_data
