from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Type, TypeVar
from app.db.models import User, Snapshot, Report, Subscription, Base

T = TypeVar("T", bound=Base)


# ---------------------------------------------------------------------------
# Shared CRUD helpers
# ---------------------------------------------------------------------------

async def _create_and_commit(db: AsyncSession, instance: T) -> T:
    """Add *instance* to the session, commit, refresh and return it."""
    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


async def _list_user_records(
    db: AsyncSession,
    model: Type[T],
    user_id: int,
    order_col,
    limit: int = 100,
) -> List[T]:
    """Return rows owned by *user_id*, ordered by *order_col* desc."""
    result = await db.execute(
        select(model)
        .where(model.user_id == user_id)
        .order_by(order_col.desc())
        .limit(limit)
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def create_user(db: AsyncSession, username: str, email: str, password_hash: str) -> User:
    return await _create_and_commit(db, User(username=username, email=email, password_hash=password_hash))


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

async def create_snapshot(db: AsyncSession, user_id: int, snapshot_data: dict) -> Snapshot:
    return await _create_and_commit(db, Snapshot(user_id=user_id, **snapshot_data))


async def list_snapshots(db: AsyncSession, user_id: int, limit: int = 100) -> List[Snapshot]:
    return await _list_user_records(db, Snapshot, user_id, Snapshot.timestamp, limit)


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------

async def create_report(db: AsyncSession, user_id: int, report_payload: dict) -> Report:
    return await _create_and_commit(db, Report(user_id=user_id, **report_payload))


async def list_reports(db: AsyncSession, user_id: int, limit: int = 100) -> List[Report]:
    return await _list_user_records(db, Report, user_id, Report.generated_at, limit)


# ---------------------------------------------------------------------------
# Subscription helpers
# ---------------------------------------------------------------------------

async def create_or_update_subscription(db: AsyncSession, user_id: int, subscription_data: dict) -> Subscription:
    existing = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .where(Subscription.provider == subscription_data.get("provider", "stripe"))
        .limit(1)
    )
    subscription = existing.scalars().first()
    if subscription:
        for key, value in subscription_data.items():
            setattr(subscription, key, value)
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
        return subscription
    return await _create_and_commit(db, Subscription(user_id=user_id, **subscription_data))


async def list_subscriptions(db: AsyncSession, user_id: int, limit: int = 50):
    return await _list_user_records(db, Subscription, user_id, Subscription.created_at, limit)
