from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Circle, CircleMember
from sqlalchemy.future import select
from pydantic import BaseModel

router = APIRouter()

class CircleCreate(BaseModel):
    name: str
    description: str = None

@router.post("/circles")
async def create_circle(
    payload: CircleCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    circle = Circle(name=payload.name, description=payload.description, owner_id=current_user.id)
    db.add(circle)
    await db.commit()
    await db.refresh(circle)
    
    # Auto-add creator as admin member
    member = CircleMember(circle_id=circle.id, user_id=current_user.id, role='admin')
    db.add(member)
    await db.commit()
    
    return circle

@router.post("/circles/{circle_id}/join")
async def join_circle(
    circle_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Check if already a member
    result = await db.execute(select(CircleMember).where(CircleMember.circle_id == circle_id, CircleMember.user_id == current_user.id))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Already a member")
        
    member = CircleMember(circle_id=circle_id, user_id=current_user.id)
    db.add(member)
    await db.commit()
    return {"message": "Joined circle"}

@router.get("/circles/{circle_id}/leaderboard")
async def get_circle_leaderboard(
    circle_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    # Get members of the circle
    result = await db.execute(select(CircleMember).where(CircleMember.circle_id == circle_id))
    members = result.scalars().all()
    user_ids = [m.user_id for m in members]

    # Get latest VEKTRA score for each member
    from app.db.models import Snapshot
    leaderboard = []
    for uid in user_ids:
        snap_res = await db.execute(
            select(Snapshot)
            .where(Snapshot.user_id == uid)
            .order_by(Snapshot.timestamp.desc())
            .limit(1)
        )
        last_snap = snap_res.scalars().first()
        leaderboard.append({
            "user_id": uid,
            "vektra_score": last_snap.vektra_score if last_snap else 0
        })

    # Sort by score descending
    leaderboard.sort(key=lambda x: x["vektra_score"], reverse=True)
    return leaderboard

