from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from app.schemas import SnapshotCreate, SnapshotOut, SnapshotStatusOut
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


@router.get("/users/{user_id}/snapshots/today", response_model=SnapshotStatusOut)
async def get_today_snapshot_status(
    user_id: int,
    target_date: date | None = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    logged = await crud.has_snapshot_for_date(db, user_id, target_date)
    return {"logged": logged}


@router.get("/users/{user_id}/snapshots", response_model=List[SnapshotOut])
async def get_snapshots(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    snaps = await crud.list_snapshots(db, user_id)
    return snaps


@router.get("/users/{user_id}/snapshots/analytics")
async def get_analytics(
    user_id: int,
    period: str = Query(default="7d", pattern="^(7d|30d|90d|1y)$"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Get historical analytics data for charts"""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    
    snapshots = await crud.list_snapshots(db, user_id, limit=365)
    
    # Filter by period
    today = date.today()
    if period == "7d":
        start_date = today - timedelta(days=7)
    elif period == "30d":
        start_date = today - timedelta(days=30)
    elif period == "90d":
        start_date = today - timedelta(days=90)
    else:  # 1y
        start_date = today - timedelta(days=365)
    
    filtered = [s for s in snapshots if s.timestamp and s.timestamp.date() >= start_date]
    
    # Aggregate by date
    daily_data = {}
    for snap in sorted(filtered, key=lambda x: x.timestamp):
        date_key = snap.timestamp.date().isoformat()
        daily_data[date_key] = {
            'date': date_key,
            'vektra_score': snap.vektra_score,
            'mood_score': snap.mood_score,
            'sleep_hours': snap.sleep_hours,
            'focus_hours': snap.focus_hours,
            'daily_income': snap.daily_income,
            'expenses': snap.expenses,
            'current_net_worth': snap.current_net_worth
        }
    
    return {
        'period': period,
        'data': list(daily_data.values())
    }


@router.get("/users/{user_id}/snapshots/comparison")
async def get_weekly_comparison(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Get comparison between current week and previous week"""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    
    snapshots = await crud.list_snapshots(db, user_id, limit=100)
    
    today = date.today()
    current_week_start = today - timedelta(days=today.weekday())
    previous_week_start = current_week_start - timedelta(days=7)
    previous_week_end = current_week_start - timedelta(days=1)
    
    # Filter snapshots for current and previous week
    current_week = [s for s in snapshots if s.timestamp and s.timestamp.date() >= current_week_start]
    previous_week = [s for s in snapshots if s.timestamp and previous_week_start <= s.timestamp.date() <= previous_week_end]
    
    # Calculate averages for each metric
    def calculate_avg(snapshots, field):
        values = [getattr(s, field) for s in snapshots if getattr(s, field) is not None]
        return sum(values) / len(values) if values else None
    
    current_metrics = {
        'vektra_score': calculate_avg(current_week, 'vektra_score'),
        'mood_score': calculate_avg(current_week, 'mood_score'),
        'sleep_hours': calculate_avg(current_week, 'sleep_hours'),
        'focus_hours': calculate_avg(current_week, 'focus_hours'),
        'daily_income': sum([s.daily_income or 0 for s in current_week]),
        'expenses': sum([s.expenses or 0 for s in current_week]),
        'net_cash_flow': sum([(s.daily_income or 0) - (s.expenses or 0) for s in current_week])
    }
    
    previous_metrics = {
        'vektra_score': calculate_avg(previous_week, 'vektra_score'),
        'mood_score': calculate_avg(previous_week, 'mood_score'),
        'sleep_hours': calculate_avg(previous_week, 'sleep_hours'),
        'focus_hours': calculate_avg(previous_week, 'focus_hours'),
        'daily_income': sum([s.daily_income or 0 for s in previous_week]),
        'expenses': sum([s.expenses or 0 for s in previous_week]),
        'net_cash_flow': sum([(s.daily_income or 0) - (s.expenses or 0) for s in previous_week])
    }
    
    # Calculate percentage changes
    def calculate_change(current, previous):
        if previous is None or previous == 0 or current is None:
            return None
        return ((current - previous) / previous) * 100
    
    changes = {
        'vektra_score': calculate_change(current_metrics['vektra_score'], previous_metrics['vektra_score']),
        'mood_score': calculate_change(current_metrics['mood_score'], previous_metrics['mood_score']),
        'sleep_hours': calculate_change(current_metrics['sleep_hours'], previous_metrics['sleep_hours']),
        'focus_hours': calculate_change(current_metrics['focus_hours'], previous_metrics['focus_hours']),
        'daily_income': calculate_change(current_metrics['daily_income'], previous_metrics['daily_income']),
        'expenses': calculate_change(current_metrics['expenses'], previous_metrics['expenses']),
        'net_cash_flow': calculate_change(current_metrics['net_cash_flow'], previous_metrics['net_cash_flow'])
    }
    
    return {
        'current_week': current_metrics,
        'previous_week': previous_metrics,
        'changes': changes,
        'current_week_logs': len(current_week),
        'previous_week_logs': len(previous_week)
    }
