from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User, Snapshot, Report, Subscription, Payment, Achievement
from app import crud

router = APIRouter()

# Admin authorization check
async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.username != "roophy":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/admin/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Get overall platform statistics"""
    
    # Total users
    total_users = await db.execute(select(func.count(User.id)))
    total_users_count = total_users.scalar() or 0
    
    # Active users (logged in last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users = await db.execute(
        select(func.count(func.distinct(Snapshot.user_id)))
        .where(Snapshot.timestamp >= seven_days_ago)
    )
    active_users_count = active_users.scalar() or 0
    
    # Total snapshots
    total_snapshots = await db.execute(select(func.count(Snapshot.id)))
    total_snapshots_count = total_snapshots.scalar() or 0
    
    # Total reports
    total_reports = await db.execute(select(func.count(Report.id)))
    total_reports_count = total_reports.scalar() or 0
    
    # Revenue from subscriptions
    total_revenue = await db.execute(
        select(func.sum(Payment.amount))
        .where(Payment.status == 'succeeded')
    )
    revenue = total_revenue.scalar() or 0
    
    # Top performers by VEKTRA score
    top_performers = await db.execute(
        select(User.username, func.avg(Snapshot.vektra_score).label('avg_score'))
        .join(Snapshot, User.id == Snapshot.user_id)
        .where(Snapshot.vektra_score.isnot(None))
        .group_by(User.id, User.username)
        .order_by(func.avg(Snapshot.vektra_score).desc())
        .limit(5)
    )
    top_performers_list = [
        {"username": row.username, "avg_score": round(row.avg_score, 1)}
        for row in top_performers
    ]
    
    return {
        "total_users": total_users_count,
        "active_users_7d": active_users_count,
        "total_snapshots": total_snapshots_count,
        "total_reports": total_reports_count,
        "total_revenue": revenue,
        "top_performers": top_performers_list
    }


@router.get("/admin/users")
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None),
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """List all users with pagination and search"""
    
    query = select(User)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )
    
    query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Get total count
    count_query = select(func.count(User.id))
    if search:
        search_pattern = f"%{search}%"
        count_query = count_query.where(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern))
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    users_list = []
    for user in users:
        # Get user stats
        snapshots_result = await db.execute(
            select(func.count(Snapshot.id)).where(Snapshot.user_id == user.id)
        )
        snapshot_count = snapshots_result.scalar() or 0
        
        reports_result = await db.execute(
            select(func.count(Report.id)).where(Report.user_id == user.id)
        )
        report_count = reports_result.scalar() or 0
        
        users_list.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "tier": user.tier,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "snapshot_count": snapshot_count,
            "report_count": report_count,
            "is_admin": user.username == "roophy"
        })
    
    return {
        "users": users_list,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Get detailed information about a specific user"""
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user stats
    snapshots_result = await db.execute(
        select(func.count(Snapshot.id)).where(Snapshot.user_id == user_id)
    )
    snapshot_count = snapshots_result.scalar() or 0
    
    # Get latest snapshot
    latest_snapshot_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(1)
    )
    latest_snapshot = latest_snapshot_result.scalars().first()
    
    # Get subscription info
    subscription_result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id, Subscription.active == True)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = subscription_result.scalars().first()
    
    # Get payment history
    payments_result = await db.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(10)
    )
    payments = payments_result.scalars().all()
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "tier": user.tier,
        "tier_expires_at": user.tier_expires_at.isoformat() if user.tier_expires_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "primary_goal": user.primary_goal,
        "north_star": user.north_star,
        "current_location": user.current_location,
        "snapshot_count": snapshot_count,
        "latest_snapshot": {
            "timestamp": latest_snapshot.timestamp.isoformat() if latest_snapshot else None,
            "vektra_score": latest_snapshot.vektra_score if latest_snapshot else None,
            "mood_score": latest_snapshot.mood_score if latest_snapshot else None
        } if latest_snapshot else None,
        "subscription": {
            "plan": subscription.plan,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "active": subscription.active
        } if subscription else None,
        "recent_payments": [
            {
                "amount": p.amount,
                "currency": p.currency,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in payments
        ]
    }


@router.put("/admin/users/{user_id}/tier")
async def update_user_tier(
    user_id: int,
    tier: str = Query(..., regex="^(free|tier1|tier2|tier3)$"),
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Update user's subscription tier"""
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.tier = tier
    db.add(user)
    await db.commit()
    
    return {"message": f"User tier updated to {tier}"}


@router.delete("/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Delete a user (cascade will delete related data)"""
    
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/admin/recent-activity")
async def get_recent_activity(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Get recent platform activity (snapshots, reports, subscriptions)"""
    
    # Recent snapshots
    snapshots_result = await db.execute(
        select(Snapshot, User.username)
        .join(User, Snapshot.user_id == User.id)
        .order_by(Snapshot.timestamp.desc())
        .limit(limit)
    )
    recent_snapshots = [
        {
            "type": "snapshot",
            "username": row.username,
            "timestamp": row.Snapshot.timestamp.isoformat() if row.Snapshot.timestamp else None,
            "vektra_score": row.Snapshot.vektra_score
        }
        for row in snapshots_result
    ]
    
    # Recent reports
    reports_result = await db.execute(
        select(Report, User.username)
        .join(User, Report.user_id == User.id)
        .order_by(Report.generated_at.desc())
        .limit(limit)
    )
    recent_reports = [
        {
            "type": "report",
            "username": row.username,
            "timestamp": row.Report.generated_at.isoformat() if row.Report.generated_at else None,
            "report_type": row.Report.report_type,
            "vektra_score": row.Report.vektra_score
        }
        for row in reports_result
    ]
    
    # Combine and sort by timestamp
    all_activity = recent_snapshots + recent_reports
    all_activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    
    return all_activity[:limit]


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


