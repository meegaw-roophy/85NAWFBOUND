import logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.models import User, Snapshot, Report, Subscription, Goal, GoalStatus

logger = logging.getLogger(__name__)

ALLOWED_SUBSCRIPTION_FIELDS = {
    "provider", "provider_customer_id", "plan", "active",
}


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_snapshot(db: AsyncSession, user_id: int, snapshot_data: dict) -> Snapshot:
    snap = Snapshot(user_id=user_id, **snapshot_data)
    db.add(snap)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error creating snapshot for user %s: %s", user_id, exc)
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Database error creating snapshot for user %s: %s", user_id, exc)
        raise
    await db.refresh(snap)
    return snap


async def create_user(db: AsyncSession, username: str, email: str, password_hash: str) -> User:
    user = User(username=username, email=email, password_hash=password_hash)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error creating user %s: %s", username, exc)
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Database error creating user %s: %s", username, exc)
        raise
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


async def create_or_update_subscription(db: AsyncSession, user_id: int, subscription_data: dict) -> Subscription:
    existing = await db.execute(select(Subscription).where(Subscription.user_id == user_id).where(Subscription.provider == subscription_data.get('provider', 'stripe')).limit(1))
    subscription = existing.scalars().first()
    if subscription:
        for key, value in subscription_data.items():
            if key not in ALLOWED_SUBSCRIPTION_FIELDS:
                logger.warning("Ignoring unknown subscription field: %s", key)
                continue
            setattr(subscription, key, value)
        db.add(subscription)
    else:
        subscription = Subscription(user_id=user_id, **subscription_data)
        db.add(subscription)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error upserting subscription for user %s: %s", user_id, exc)
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Database error upserting subscription for user %s: %s", user_id, exc)
        raise
    await db.refresh(subscription)
    return subscription


async def list_subscriptions(db: AsyncSession, user_id: int, limit: int = 50):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.created_at.desc()).limit(limit))
    return result.scalars().all()


async def create_report(db: AsyncSession, user_id: int, report_payload: dict) -> Report:
    rpt = Report(user_id=user_id, **report_payload)
    db.add(rpt)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.error("Integrity error creating report for user %s: %s", user_id, exc)
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error("Database error creating report for user %s: %s", user_id, exc)
        raise
    await db.refresh(rpt)
    return rpt


# --- Goals ---

async def create_goal(db: AsyncSession, user_id: int, goal_data: dict) -> Goal:
    goal = Goal(user_id=user_id, **goal_data)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def list_goals(db: AsyncSession, user_id: int, status: Optional[str] = None, limit: int = 100) -> List[Goal]:
    query = select(Goal).where(Goal.user_id == user_id)
    if status:
        query = query.where(Goal.status == status)
    query = query.order_by(Goal.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_goal(db: AsyncSession, goal_id: int) -> Optional[Goal]:
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    return result.scalars().first()


async def update_goal(db: AsyncSession, goal: Goal, update_data: dict) -> Goal:
    for key, value in update_data.items():
        if value is not None:
            setattr(goal, key, value)
    # Auto-complete if target reached
    if goal.target_value and goal.current_value >= goal.target_value:
        goal.status = GoalStatus.completed
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_goal(db: AsyncSession, goal: Goal) -> None:
    await db.delete(goal)
    await db.commit()
