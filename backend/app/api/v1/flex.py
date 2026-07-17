from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Snapshot
from sqlalchemy.future import select
from datetime import datetime

router = APIRouter()

@router.get("/snapshots/{snapshot_id}/flex-card")
async def get_flex_card_data(
    snapshot_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Returns data formatted for a social 'Flex Card'.
    The frontend can use this to render a beautiful image for Instagram/TikTok.
    """
    result = await db.execute(select(Snapshot).where(Snapshot.id == snapshot_id, Snapshot.user_id == current_user.id))
    snap = result.scalars().first()
    
    if not snap:
        raise HTTPException(status_code=404, detail="Snapshot not found")
        
    # Return data for the card
    return {
        "username": current_user.username,
        "date": snap.log_date,
        "vektra_score": snap.vektra_score,
        "viral_caption": "I'm optimizing my life at the top of the VEKTRA scale. Join the squad.",
        "badge_rarity": "Legendary" if (snap.vektra_score or 0) > 90 else "Rare" if (snap.vektra_score or 0) > 75 else "Common",
        "app_link": "https://vektra.app/join/squad/" + str(current_user.id)
    }
