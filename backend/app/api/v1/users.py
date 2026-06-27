from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User
from app.core.deps import get_current_user
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, time

router = APIRouter(prefix="/users", tags=["users"])


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    primary_goal: Optional[str] = None
    north_star: Optional[str] = None
    north_star_deadline: Optional[date] = None
    initial_net_worth: Optional[float] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    preferred_feedback_tone: Optional[str] = None
    ai_tone_language: Optional[str] = None
    reminder_time: Optional[time] = None
    current_location: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    primary_goal: Optional[str] = None
    north_star: Optional[str] = None
    north_star_deadline: Optional[date] = None
    initial_net_worth: Optional[float] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    preferred_feedback_tone: Optional[str] = None
    ai_tone_language: Optional[str] = None
    tier: Optional[str] = None
    tier_expires_at: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserOut)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current authenticated user profile."""
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update current user profile — north star, preferences, etc."""
    update_data = payload.model_dump(exclude_none=True)

    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
