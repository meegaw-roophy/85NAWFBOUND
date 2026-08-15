from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User, WeeklyQuestion, MonthlyQuestion
from app.core.deps import get_current_user
from datetime import datetime
from typing import Optional

router = APIRouter()


@router.post("/users/{user_id}/weekly-questions")
async def submit_weekly_questions(
    user_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Submit weekly reflection questions"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if already submitted for this week
    current_week = datetime.utcnow().isocalendar()[1]
    current_year = datetime.utcnow().year
    
    existing = await db.execute(
        select(WeeklyQuestion).where(
            WeeklyQuestion.user_id == user_id,
            WeeklyQuestion.week_number == current_week,
            WeeklyQuestion.year == current_year
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already submitted for this week")
    
    weekly_q = WeeklyQuestion(
        user_id=user_id,
        week_number=payload.get('week_number', current_week),
        year=payload.get('year', current_year),
        biggest_win=payload.get('biggest_win'),
        blockers=payload.get('blockers'),
        next_week_focus=payload.get('next_week_focus'),
        satisfaction=payload.get('satisfaction')
    )
    
    db.add(weekly_q)
    await db.commit()
    await db.refresh(weekly_q)
    
    return {"message": "Weekly questions saved", "id": weekly_q.id}


@router.get("/users/{user_id}/weekly-questions")
async def get_weekly_questions(
    user_id: int,
    week: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get weekly questions for a specific week"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    current_week = week or datetime.utcnow().isocalendar()[1]
    current_year = year or datetime.utcnow().year
    
    result = await db.execute(
        select(WeeklyQuestion).where(
            WeeklyQuestion.user_id == user_id,
            WeeklyQuestion.week_number == current_week,
            WeeklyQuestion.year == current_year
        )
    )
    weekly_q = result.scalar_one_or_none()
    
    if not weekly_q:
        raise HTTPException(status_code=404, detail="No weekly questions found for this week")
    
    return {
        "id": weekly_q.id,
        "week_number": weekly_q.week_number,
        "year": weekly_q.year,
        "biggest_win": weekly_q.biggest_win,
        "blockers": weekly_q.blockers,
        "next_week_focus": weekly_q.next_week_focus,
        "satisfaction": weekly_q.satisfaction,
        "created_at": weekly_q.created_at
    }


@router.post("/users/{user_id}/monthly-questions")
async def submit_monthly_questions(
    user_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Submit monthly goal questions"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if already submitted for this month
    current_month = datetime.utcnow().month
    current_year = datetime.utcnow().year
    
    existing = await db.execute(
        select(MonthlyQuestion).where(
            MonthlyQuestion.user_id == user_id,
            MonthlyQuestion.month == current_month,
            MonthlyQuestion.year == current_year
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already submitted for this month")
    
    monthly_q = MonthlyQuestion(
        user_id=user_id,
        month=payload.get('month', current_month),
        year=payload.get('year', current_year),
        monthly_goal=payload.get('monthly_goal'),
        habits_to_build=payload.get('habits_to_build'),
        success_definition=payload.get('success_definition'),
        confidence=payload.get('confidence')
    )
    
    db.add(monthly_q)
    await db.commit()
    await db.refresh(monthly_q)
    
    return {"message": "Monthly questions saved", "id": monthly_q.id}


@router.get("/users/{user_id}/monthly-questions")
async def get_monthly_questions(
    user_id: int,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get monthly questions for a specific month"""
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    current_month = month or datetime.utcnow().month
    current_year = year or datetime.utcnow().year
    
    result = await db.execute(
        select(MonthlyQuestion).where(
            MonthlyQuestion.user_id == user_id,
            MonthlyQuestion.month == current_month,
            MonthlyQuestion.year == current_year
        )
    )
    monthly_q = result.scalar_one_or_none()
    
    if not monthly_q:
        raise HTTPException(status_code=404, detail="No monthly questions found for this month")
    
    return {
        "id": monthly_q.id,
        "month": monthly_q.month,
        "year": monthly_q.year,
        "monthly_goal": monthly_q.monthly_goal,
        "habits_to_build": monthly_q.habits_to_build,
        "success_definition": monthly_q.success_definition,
        "confidence": monthly_q.confidence,
        "created_at": monthly_q.created_at
    }
