from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas import UserPointsOut

router = APIRouter()


# Read-only on purpose: XP is only ever awarded by the server when a new
# daily log is saved, so there is no endpoint a client could use to grant it.
@router.get("/points", response_model=UserPointsOut)
async def get_user_points(db: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    points = await crud.get_or_create_user_points(db, current_user.id)
    return crud.user_points_payload(points)
