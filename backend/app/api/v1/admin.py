import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User, Snapshot
from app import crud

router = APIRouter()

@router.post("/admin/seed-data")
async def seed_data(
    db: AsyncSession = Depends(get_session), 
    current_user: User = Depends(get_current_user)
):
    if current_user.username != "roophy":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Generate 30 days of data
    for i in range(30):
        # Ensure we don't duplicate existing logs
        log_date = datetime.utcnow() - timedelta(days=i)
        if await crud.has_snapshot_for_date(db, current_user.id, log_date.date()):
            continue

        snapshot_data = {
            "log_date": log_date.date(),
            "mood_score": random.randint(1, 10),
            "energy_level": random.randint(1, 10),
            "focus_hours": random.uniform(1, 8),
            "daily_income": random.uniform(0, 1000),
            "expenses": random.uniform(0, 500),
            "target_hit_bool": random.choice([True, False])
        }
        await crud.create_snapshot(db, current_user.id, snapshot_data)
    
    return {"message": "30 days of data seeded successfully"}

