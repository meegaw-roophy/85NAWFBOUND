from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.models import User, Snapshot, Report, Subscription, Payment, Goal


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_snapshot(db: AsyncSession, user_id: int, snapshot_data: dict) -> Snapshot:
    # ── Avoid duplicate entries for the same day ──
    target_date = None
    if snapshot_data.get('log_date') is not None:
        target_date = snapshot_data['log_date']
    elif snapshot_data.get('timestamp') is not None:
        target_date = snapshot_data['timestamp'].date()
    else:
        target_date = datetime.utcnow().date()

    if target_date is not None:
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        existing_result = await db.execute(
            select(Snapshot)
            .where(Snapshot.user_id == user_id)
            .where(Snapshot.timestamp >= start_of_day)
            .where(Snapshot.timestamp < end_of_day)
            .order_by(Snapshot.timestamp.desc())
            .limit(1)
        )
        existing = existing_result.scalars().first()
        if existing:
            existing.is_duplicate = True
            return existing

    # ── Get previous snapshot for variance calculations ──
    prev_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(1)
    )
    previous = prev_result.scalars().first()
    prev_dict = {}
    if previous:
        prev_dict = {
            'current_net_worth': previous.current_net_worth,
            'expenses': previous.expenses,
            'current_capital': previous.current_capital,
        }

    # ── Run VEKTRA score engine ──
    from app.services.vektra_engine import calculate_vektra_score
    score_result = calculate_vektra_score(snapshot_data, prev_dict)

    # ── Merge computed scores into snapshot data ──
    snapshot_data['vektra_score']          = score_result.vektra_score
    snapshot_data['burn_rate']             = score_result.burn_rate
    snapshot_data['net_worth_variance']    = score_result.net_worth_variance
    snapshot_data['resilience_score']      = score_result.resilience_score
    snapshot_data['survival_runway']       = score_result.survival_runway
    snapshot_data['procrastination_delta'] = score_result.procrastination_delta
    snapshot_data['leverage_score']        = score_result.leverage_score
    snapshot_data['opportunity_cost_score']= score_result.opportunity_cost_score

    # ── Save to database ──
    snap = Snapshot(user_id=user_id, **snapshot_data)
    snap.is_duplicate = False
    db.add(snap)
    await db.commit()
    await db.refresh(snap)
    return snap


async def create_user(db: AsyncSession, username: str, email: str, password_hash: str, full_name: Optional[str] = None, dob: Optional[date] = None, current_location: Optional[str] = None, language: Optional[str] = None, primary_goal: Optional[str] = None) -> User:
    user = User(username=username, email=email, password_hash=password_hash, full_name=full_name, dob=dob, current_location=current_location, language=language, primary_goal=primary_goal)
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


async def has_snapshot_for_date(db: AsyncSession, user_id: int, target_date: Optional[datetime.date] = None) -> bool:
    if target_date is None:
        target_date = datetime.utcnow().date()

    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)
    result = await db.execute(
        select(Snapshot.id)
        .where(Snapshot.user_id == user_id)
        .where(Snapshot.timestamp >= start_of_day)
        .where(Snapshot.timestamp < end_of_day)
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


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


async def create_payment(db: AsyncSession, user_id: int, payment_data: dict) -> Payment:
    payment = Payment(user_id=user_id, **payment_data)
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def update_payment_status(db: AsyncSession, payment_id: int, status: str, external_response: Optional[dict] = None, provider_payment_id: Optional[str] = None) -> Optional[Payment]:
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalars().first()
    if not payment:
        return None
    payment.status = status
    if provider_payment_id is not None:
        payment.provider_payment_id = provider_payment_id
    if external_response is not None:
        payment.external_response = external_response
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment


async def list_payments(db: AsyncSession, user_id: int, limit: int = 50) -> List[Payment]:
    result = await db.execute(select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc()).limit(limit))
    return result.scalars().all()


async def create_report(db: AsyncSession, user_id: int, report_payload: dict) -> Report:
    rpt = Report(user_id=user_id, **report_payload)
    db.add(rpt)
    await db.commit()
    await db.refresh(rpt)
    return rpt


async def create_goal(db: AsyncSession, user_id: int, goal_data: dict) -> Goal:
    goal = Goal(user_id=user_id, **goal_data)
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def list_goals(db: AsyncSession, user_id: int, limit: int = 100) -> List[Goal]:
    result = await db.execute(select(Goal).where(Goal.user_id == user_id).order_by(Goal.created_at.desc()).limit(limit))
    return result.scalars().all()


async def get_goal_by_id(db: AsyncSession, goal_id: int, user_id: int) -> Optional[Goal]:
    result = await db.execute(select(Goal).where(Goal.id == goal_id).where(Goal.user_id == user_id))
    return result.scalars().first()


async def update_goal(db: AsyncSession, goal: Goal, goal_data: dict) -> Goal:
    for key, value in goal_data.items():
        setattr(goal, key, value)
    if goal_data.get('completed') and not goal.completion_date:
        goal.completion_date = datetime.utcnow()
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_goal(db: AsyncSession, goal_id: int, user_id: int) -> bool:
    result = await db.execute(select(Goal).where(Goal.id == goal_id).where(Goal.user_id == user_id))
    goal = result.scalars().first()
    if not goal:
        return False
    await db.delete(goal)
    await db.commit()
    return True


async def calculate_goal_progress(db: AsyncSession, user_id: int) -> dict:
    goals = await list_goals(db, user_id)
    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if g.completed)
    progress_pct = (completed_goals / total_goals * 100) if total_goals > 0 else 0
    next_milestone = next((g for g in goals if not g.completed), None)
    return {
        'total_goals': total_goals,
        'completed_goals': completed_goals,
        'progress_pct': progress_pct,
        'next_milestone': next_milestone.title if next_milestone else None
    }


async def predict_goal_completion(db: AsyncSession, user_id: int) -> dict:
    """Predict when user will reach their North Star goal based on trajectory"""
    snapshots = await list_snapshots(db, user_id, limit=90)
    
    if len(snapshots) < 7:
        return {
            'has_prediction': False,
            'reason': 'Need at least 7 days of data for prediction'
        }
    
    # Calculate average VEKTRA score trend
    recent_scores = [s.vektra_score for s in snapshots if s.vektra_score]
    if len(recent_scores) < 7:
        return {
            'has_prediction': False,
            'reason': 'Insufficient score data'
        }
    
    # Split into two halves to calculate trend
    mid_point = len(recent_scores) // 2
    first_half_avg = sum(recent_scores[:mid_point]) / mid_point
    second_half_avg = sum(recent_scores[mid_point:]) / (len(recent_scores) - mid_point)
    
    # Calculate weekly improvement rate
    weekly_improvement = second_half_avg - first_half_avg
    
    # Get user's current score
    current_score = recent_scores[0]
    
    # Target is 100 (perfect VEKTRA score)
    target_score = 100
    remaining = target_score - current_score
    
    if weekly_improvement <= 0:
        return {
            'has_prediction': False,
            'reason': 'Score is not trending upward',
            'current_score': current_score,
            'trend': 'declining' if weekly_improvement < 0 else 'stable'
        }
    
    # Calculate weeks to reach target
    weeks_to_target = remaining / weekly_improvement
    
    # Cap at reasonable maximum (5 years)
    if weeks_to_target > 260:
        return {
            'has_prediction': True,
            'prediction': '5+ years',
            'weeks_remaining': weeks_to_target,
            'current_score': current_score,
            'weekly_improvement': weekly_improvement,
            'confidence': 'low'
        }
    
    # Convert to months/years
    if weeks_to_target < 4:
        prediction = f"{int(weeks_to_target)} weeks"
    elif weeks_to_target < 52:
        prediction = f"{int(weeks_to_target / 4.3)} months"
    else:
        prediction = f"{int(weeks_to_target / 52)} years"
    
    # Calculate confidence based on data consistency
    score_variance = sum((s - current_score) ** 2 for s in recent_scores) / len(recent_scores)
    confidence = 'high' if score_variance < 100 else 'medium' if score_variance < 400 else 'low'
    
    return {
        'has_prediction': True,
        'prediction': prediction,
        'weeks_remaining': weeks_to_target,
        'current_score': current_score,
        'weekly_improvement': weekly_improvement,
        'confidence': confidence
    }
