from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime, timedelta

from app.db.session import get_session
from app.db.models import Snapshot, Goal, GoalStatus
from app.core.deps import get_current_user

router = APIRouter()


@router.get("/users/{user_id}/analytics/summary")
async def get_analytics_summary(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    since = datetime.utcnow() - timedelta(days=days)

    # Fetch snapshots within period
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id, Snapshot.timestamp >= since)
        .order_by(Snapshot.timestamp.asc())
    )
    snapshots = result.scalars().all()

    # Compute aggregates
    moods = [s.mood for s in snapshots if s.mood is not None]
    energies = [s.energy for s in snapshots if s.energy is not None]
    focus_scores = [s.focus for s in snapshots if s.focus is not None]
    incomes = [s.income for s in snapshots if s.income is not None]
    expenses = [s.expenses for s in snapshots if s.expenses is not None]

    # Goals summary
    goals_result = await db.execute(select(Goal).where(Goal.user_id == user_id))
    goals = goals_result.scalars().all()
    active_goals = [g for g in goals if g.status == GoalStatus.active]
    completed_goals = [g for g in goals if g.status == GoalStatus.completed]

    # Build trend data (daily averages)
    daily_data = {}
    for s in snapshots:
        day = s.timestamp.strftime("%Y-%m-%d") if s.timestamp else None
        if not day:
            continue
        if day not in daily_data:
            daily_data[day] = {"moods": [], "incomes": [], "expenses": []}
        if s.mood is not None:
            daily_data[day]["moods"].append(s.mood)
        if s.income is not None:
            daily_data[day]["incomes"].append(s.income)
        if s.expenses is not None:
            daily_data[day]["expenses"].append(s.expenses)

    trends = []
    for day, data in sorted(daily_data.items()):
        trends.append({
            "date": day,
            "avg_mood": round(sum(data["moods"]) / len(data["moods"]), 1) if data["moods"] else None,
            "total_income": sum(data["incomes"]) if data["incomes"] else None,
            "total_expenses": sum(data["expenses"]) if data["expenses"] else None,
        })

    return {
        "period_days": days,
        "snapshot_count": len(snapshots),
        "wellness": {
            "avg_mood": round(sum(moods) / len(moods), 1) if moods else None,
            "avg_energy": round(sum(energies) / len(energies), 1) if energies else None,
            "avg_focus": round(sum(focus_scores) / len(focus_scores), 1) if focus_scores else None,
            "mood_trend": _compute_trend(moods),
        },
        "financial": {
            "total_income": round(sum(incomes), 2) if incomes else 0,
            "total_expenses": round(sum(expenses), 2) if expenses else 0,
            "net_savings": round(sum(incomes) - sum(expenses), 2) if incomes and expenses else None,
        },
        "goals": {
            "total": len(goals),
            "active": len(active_goals),
            "completed": len(completed_goals),
            "completion_rate": round(len(completed_goals) / len(goals) * 100, 1) if goals else 0,
        },
        "trends": trends,
    }


def _compute_trend(values: list) -> Optional[str]:
    if len(values) < 2:
        return None
    midpoint = len(values) // 2
    first_half_avg = sum(values[:midpoint]) / midpoint
    second_half_avg = sum(values[midpoint:]) / (len(values) - midpoint)
    diff = second_half_avg - first_half_avg
    if diff > 0.5:
        return "improving"
    elif diff < -0.5:
        return "declining"
    return "stable"
