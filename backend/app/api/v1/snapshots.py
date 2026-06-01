from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.schemas import SnapshotCreate, SnapshotOut
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user

router = APIRouter()


@router.post("/users/{user_id}/snapshots", response_model=SnapshotOut)
async def add_snapshot(user_id: int, payload: SnapshotCreate, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    snap = await crud.create_snapshot(db, user_id, payload.dict(exclude_none=True))
    return snap


@router.get("/users/{user_id}/snapshots", response_model=List[SnapshotOut])
async def get_snapshots(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    snaps = await crud.list_snapshots(db, user_id)
    return snaps
