from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import Snapshot
from sqlalchemy import select, func
import numpy as np

router = APIRouter()

@router.get("/insights/profitability-correlation")
async def get_profitability_insights(
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """
    Analyzes the correlation between 'focus_hours' and 'daily_income'.
    Identifies the 'Profitability Sweet Spot'.
    """
    # Get last 60 days of snapshots
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == current_user.id)
        .order_by(Snapshot.timestamp.desc())
        .limit(60)
    )
    snaps = result.scalars().all()
    
    # Extract data
    data = [(s.focus_hours, s.daily_income) for s in snaps if s.focus_hours is not None and s.daily_income is not None]
    
    if len(data) < 10:
        return {"message": "Need more data to calculate your profit potential."}
    
    focus_hours = np.array([d[0] for d in data])
    income = np.array([d[1] for d in data])
    
    # Calculate correlation
    correlation = np.corrcoef(focus_hours, income)[0, 1]
    
    # Find "Sweet Spot" (highest income quartile focus range)
    # This gives the user a concrete target
    top_quartile_income = np.percentile(income, 75)
    sweet_spot_focus = [f for f, i in data if i >= top_quartile_income]
    
    avg_sweet_spot = np.mean(sweet_spot_focus) if sweet_spot_focus else 0
    
    return {
        "correlation_coefficient": round(correlation, 2),
        "your_profit_sweet_spot_focus": round(float(avg_sweet_spot), 1),
        "insight": f"When you hit {round(float(avg_sweet_spot), 1)} focus hours, your income peaks. "
                   f"{'Your consistency is paying off!' if correlation > 0.5 else 'Try experimenting with your focus hours to boost income.'}"
    }
