from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Wager, CircleMember
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
    return {"message": "Wager created. Circle members can now match the pot."}
