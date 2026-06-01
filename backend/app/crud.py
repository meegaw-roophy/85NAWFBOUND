from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.models import User, Snapshot, Report, Subscription


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_snapshot(db: AsyncSession, user_id: int, snapshot_data: dict) -> Snapshot:
    snap = Snapshot(user_id=user_id, **snapshot_data)
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


async def create_user(db: AsyncSession, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def list_snapshots(db: AsyncSession, user_id: int, limit: int = 100) -> List[Snapshot]:
    result = await db.execute(select(Snapshot).where(Snapshot.user_id == user_id).order_by(Snapshot.timestamp.desc()).limit(limit))
    return result.scalars().all()


async def list_reports(db: AsyncSession, user_id: int, limit: int = 100) -> List[Report]:
    result = await db.execute(select(Report).where(Report.user_id == user_id).order_by(Report.generated_at.desc()).limit(limit))
    return result.scalars().all()


async def create_or_update_subscription(db: AsyncSession, user_id: int, subscription_data: dict) -> 'Subscription':
    existing = await db.execute(select(Subscription).where(Subscription.user_id == user_id).where(Subscription.provider == subscription_data.get('provider', 'stripe')).limit(1))
    subscription = existing.scalars().first()
    if subscription:
        for key, value in subscription_data.items():
            setattr(subscription, key, value)
        db.add(subscription)
    else:
        subscription = Subscription(user_id=user_id, **subscription_data)
        db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def list_subscriptions(db: AsyncSession, user_id: int, limit: int = 50):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.created_at.desc()).limit(limit))
    return result.scalars().all()


async def create_report(db: AsyncSession, user_id: int, report_payload: dict) -> Report:
    rpt = Report(user_id=user_id, **report_payload)
    db.add(rpt)
    await db.commit()
    await db.refresh(rpt)
    return rpt
