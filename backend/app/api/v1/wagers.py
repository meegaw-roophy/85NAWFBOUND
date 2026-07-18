from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Wager, CircleMember, WagerParticipant
from sqlalchemy.future import select
from pydantic import BaseModel

router = APIRouter()

class WagerCreate(BaseModel):
    circle_id: int
    amount: float

@router.post("/wagers")
async def create_wager(
    payload: WagerCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Verify user is in the circle
    result = await db.execute(select(CircleMember).where(CircleMember.circle_id == payload.circle_id, CircleMember.user_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="You must be in the circle to create a wager")
        
    wager = Wager(circle_id=payload.circle_id, amount=payload.amount)
    db.add(wager)
    await db.commit()
    await db.refresh(wager)

    # Auto-add creator as the first participant
    participant = WagerParticipant(wager_id=wager.id, user_id=current_user.id)
    db.add(participant)
    await db.commit()
    return {"message": "Wager created. Circle members can now match the pot.", "wager_id": wager.id}

@router.post("/wagers/{wager_id}/match")
async def match_wager(
    wager_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Check if wager exists
    result = await db.execute(select(Wager).where(Wager.id == wager_id))
    wager = result.scalars().first()
    if not wager:
        raise HTTPException(status_code=404, detail="Wager not found")

    # Verify user is in the circle
    result = await db.execute(select(CircleMember).where(CircleMember.circle_id == wager.circle_id, CircleMember.user_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="You must be in the circle to match this wager")

    # Check if already matched
    result = await db.execute(select(WagerParticipant).where(WagerParticipant.wager_id == wager_id, WagerParticipant.user_id == current_user.id))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="You have already joined this wager")

    participant = WagerParticipant(wager_id=wager_id, user_id=current_user.id)
    db.add(participant)
    await db.commit()

    return {"message": "Wager matched successfully"}

