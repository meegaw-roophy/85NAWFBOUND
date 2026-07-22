from datetime import datetime, date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.models import User, Snapshot, Report, Subscription, Payment, Goal
from collections.abc import Sequence
import csv
import json


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

        # ── Calculate current streak to pass to score engine ──
    # Check current streak up to today
    today = date.today()
    check_date = today
    current_streak = 0
    
    # We fetch existing snapshot logs to construct the streak
    recent_snaps_result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(100)
    )
    recent_snaps = recent_snaps_result.scalars().all()
    snap_dates = {s.log_date or s.timestamp.date() for s in recent_snaps if s.log_date or s.timestamp}
    
    # If yesterday was logged, or today was logged, count streak
    yesterday = today - timedelta(days=1)
    if yesterday in snap_dates or today in snap_dates:
        # Check consecutive days backward
        check_date = today if today in snap_dates else yesterday
        while check_date in snap_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    # ── Run VEKTRA score engine ──
    from app.services.vektra_engine import calculate_vektra_score
    score_result = calculate_vektra_score(snapshot_data, prev_dict, current_streak=current_streak)

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


    return result.scalars().all()


async def list_reports(db: AsyncSession, user_id: int, limit: int = 100) -> List[Report]:
    result = await db.execute(select(Report).where(Report.user_id == user_id).order_by(Report.generated_at.desc()).limit(limit))
    return result.scalars().all()


async def get_report_by_id(db: AsyncSession, report_id: int) -> Optional[Report]:
    result = await db.execute(select(Report).where(Report.id == report_id))
    return result.scalars().first()


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

async def list_snapshots(db: AsyncSession, user_id: int, limit: int = 100, offset: int = 0) -> List[Snapshot]:
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


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


# ── ACHIEVEMENT CRUD ──
async def create_achievement(db: AsyncSession, user_id: int, achievement_data: dict) -> Achievement:
    """Create a new achievement for a user"""
    from app.db.models import Achievement
    achievement = Achievement(
        user_id=user_id,
        achievement_id=achievement_data['achievement_id'],
        title=achievement_data['title'],
        description=achievement_data.get('description'),
        icon=achievement_data.get('icon'),
        rarity=achievement_data.get('rarity', 'common'),
        progress=achievement_data.get('progress', 0.0),
        completed=achievement_data.get('completed', False),
        completed_at=datetime.datetime.utcnow() if achievement_data.get('completed') else None
    )
    db.add(achievement)
    await db.commit()
    await db.refresh(achievement)
    return achievement


async def list_achievements(db: AsyncSession, user_id: int) -> list:
    """Get all achievements for a user"""
    from app.db.models import Achievement
    result = await db.execute(
        select(Achievement)
        .where(Achievement.user_id == user_id)
        .order_by(Achievement.created_at.desc())
    )
    return result.scalars().all()


async def get_achievement_by_id(db: AsyncSession, achievement_id: int, user_id: int) -> Achievement:
    """Get a specific achievement by ID"""
    from app.db.models import Achievement
    result = await db.execute(
        select(Achievement)
        .where(Achievement.id == achievement_id)
        .where(Achievement.user_id == user_id)
    )
    return result.scalars().first()


async def update_achievement(db: AsyncSession, achievement: Achievement, update_data: dict) -> Achievement:
    """Update an achievement"""
    for key, value in update_data.items():
        if hasattr(achievement, key):
            setattr(achievement, key, value)
    
    if update_data.get('completed') and not achievement.completed_at:
        achievement.completed_at = datetime.datetime.utcnow()
    
    await db.commit()
    await db.refresh(achievement)
    return achievement


# ── ACHIEVEMENT DEFINITIONS ──
ACHIEVEMENT_DEFINITIONS = {
    'first_log': {
        'title': 'First Log',
        'description': 'Logged your first snapshot',
        'icon': '🎯',
        'rarity': 'common'
    },
    'streak_3': {
        'title': '3-Day Streak',
        'description': 'Logged for 3 consecutive days',
        'icon': '🔥',
        'rarity': 'common'
    },
    'streak_7': {
        'title': '7-Day Streak',
        'description': 'Logged for 7 consecutive days',
        'icon': '🔥',
        'rarity': 'rare'
    },
    'streak_30': {
        'title': '30-Day Streak',
        'description': 'Logged for 30 consecutive days',
        'icon': '🔥',
        'rarity': 'epic'
    },
    'score_60': {
        'title': 'Score 60',
        'description': 'Achieved a VEKTRA score of 60+',
        'icon': '⭐',
        'rarity': 'common'
    },
    'score_80': {
        'title': 'Score 80',
        'description': 'Achieved a VEKTRA score of 80+',
        'icon': '⭐',
        'rarity': 'rare'
    },
    'score_90': {
        'title': 'Score 90',
        'description': 'Achieved a VEKTRA score of 90+',
        'icon': '⭐',
        'rarity': 'epic'
    },
    'goal_complete': {
        'title': 'Goal Complete',
        'description': 'Completed your first goal',
        'icon': '🎯',
        'rarity': 'rare'
    },
    'goals_5': {
        'title': '5 Goals',
        'description': 'Completed 5 goals',
        'icon': '🎯',
        'rarity': 'epic'
    },
    'perfect_day': {
        'title': 'Perfect Day',
        'description': 'Logged with all metrics filled',
        'icon': '✨',
        'rarity': 'rare'
    }
}


async def check_and_unlock_achievements(db: AsyncSession, user_id: int, snapshot: Snapshot = None) -> list:
    """Check for new achievements based on user data"""
    from app.db.models import Achievement
    
    new_achievements = []
    existing_achievements = await list_achievements(db, user_id)
    existing_ids = {a.achievement_id for a in existing_achievements}
    
    # Get user data
    snapshots = await list_snapshots(db, user_id, limit=100)
    goals = await list_goals(db, user_id)
    
    # Check first_log
    if 'first_log' not in existing_ids and len(snapshots) >= 1:
        achievement = await create_achievement(db, user_id, {
            'achievement_id': 'first_log',
            **ACHIEVEMENT_DEFINITIONS['first_log'],
            'completed': True
        })
        new_achievements.append(achievement)
    
    # Check streak achievements
    if len(snapshots) >= 3:
        # Calculate consecutive days
        dates = sorted([s.log_date or s.timestamp.date() for s in snapshots if s.log_date or s.timestamp], reverse=True)
        streak = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                streak += 1
            else:
                break
        
        if streak >= 3 and 'streak_3' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'streak_3',
                **ACHIEVEMENT_DEFINITIONS['streak_3'],
                'completed': True
            })
            new_achievements.append(achievement)
        
        if streak >= 7 and 'streak_7' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'streak_7',
                **ACHIEVEMENT_DEFINITIONS['streak_7'],
                'completed': True
            })
            new_achievements.append(achievement)
        
        if streak >= 30 and 'streak_30' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'streak_30',
                **ACHIEVEMENT_DEFINITIONS['streak_30'],
                'completed': True
            })
            new_achievements.append(achievement)
    
    # Check score achievements
    if snapshot and snapshot.vektra_score:
        if snapshot.vektra_score >= 60 and 'score_60' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'score_60',
                **ACHIEVEMENT_DEFINITIONS['score_60'],
                'completed': True
            })
            new_achievements.append(achievement)
        
        if snapshot.vektra_score >= 80 and 'score_80' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'score_80',
                **ACHIEVEMENT_DEFINITIONS['score_80'],
                'completed': True
            })
            new_achievements.append(achievement)
        
        if snapshot.vektra_score >= 90 and 'score_90' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'score_90',
                **ACHIEVEMENT_DEFINITIONS['score_90'],
                'completed': True
            })
            new_achievements.append(achievement)
    
    # Check goal achievements
    completed_goals = sum(1 for g in goals if g.completed)
    if completed_goals >= 1 and 'goal_complete' not in existing_ids:
        achievement = await create_achievement(db, user_id, {
            'achievement_id': 'goal_complete',
            **ACHIEVEMENT_DEFINITIONS['goal_complete'],
            'completed': True
        })
        new_achievements.append(achievement)
    
    if completed_goals >= 5 and 'goals_5' not in existing_ids:
        achievement = await create_achievement(db, user_id, {
            'achievement_id': 'goals_5',
            **ACHIEVEMENT_DEFINITIONS['goals_5'],
            'completed': True
        })
        new_achievements.append(achievement)
    
    # Check perfect day
    if snapshot:
        required_fields = ['mood_score', 'energy_level', 'focus_level', 'sleep_hours', 'daily_income', 'expenses']
        filled_fields = sum(1 for field in required_fields if getattr(snapshot, field) is not None)
        if filled_fields == len(required_fields) and 'perfect_day' not in existing_ids:
            achievement = await create_achievement(db, user_id, {
                'achievement_id': 'perfect_day',
                **ACHIEVEMENT_DEFINITIONS['perfect_day'],
                'completed': True
            })
            new_achievements.append(achievement)
    
    return new_achievements


# ── STREAK CALENDAR ──
async def get_streak_calendar(db: AsyncSession, user_id: int, days: int = 365) -> dict:
    """Get streak calendar data for GitHub-style visualization"""
    snapshots = await list_snapshots(db, user_id, limit=days)
    
    # Build date map
    date_map = {}
    for snap in snapshots:
        date = snap.log_date or snap.timestamp.date()
        if snap.vektra_score:
            date_map[date.isoformat()] = snap.vektra_score
    
    # Calculate calendar data
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    calendar_data = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.isoformat()
        score = date_map.get(date_str, 0)
        
        calendar_data.append({
            'date': date_str,
            'score': score,
            'logged': score > 0
        })
        
        current_date += timedelta(days=1)
    
    # Calculate current streak
    current_streak = 0
    today = date.today()
    check_date = today
    
    while check_date.isoformat() in date_map:
        current_streak += 1
        check_date -= timedelta(days=1)
    
    # Calculate longest streak
    longest_streak = 0
    temp_streak = 0
    sorted_dates = sorted(date_map.keys())
    
    for i in range(len(sorted_dates)):
        if i == 0:
            temp_streak = 1
        else:
            prev_date = date.fromisoformat(sorted_dates[i-1])
            curr_date = date.fromisoformat(sorted_dates[i])
            if (curr_date - prev_date).days == 1:
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak)
    
    # Calculate total days logged
    total_logged = len(date_map)
    
    return {
        'calendar_data': calendar_data,
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_logged': total_logged,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }


# ── ADVANCED FINANCIAL METRICS ──
async def calculate_financial_health(db: AsyncSession, user_id: int) -> dict:
    """Calculate comprehensive financial health metrics"""
    snapshots = await list_snapshots(db, user_id, limit=90)
    
    if len(snapshots) < 7:
        return {
            'has_data': False,
            'reason': 'Need at least 7 days of financial data'
        }
    
    # Extract financial data
    income_data = [s.daily_income for s in snapshots if s.daily_income]
    expense_data = [s.expenses for s in snapshots if s.expenses]
    savings_data = [s.savings_investments for s in snapshots if s.savings_investments]
    net_worth_data = [s.current_net_worth for s in snapshots if s.current_net_worth]
    
    # Calculate averages
    avg_income = sum(income_data) / len(income_data) if income_data else 0
    avg_expenses = sum(expense_data) / len(expense_data) if expense_data else 0
    avg_savings = sum(savings_data) / len(savings_data) if savings_data else 0
    
    # Calculate savings rate
    savings_rate = (avg_savings / avg_income * 100) if avg_income > 0 else 0
    
    # Calculate burn rate (average monthly expenses)
    burn_rate = avg_expenses * 30 if avg_expenses else 0
    
    # Calculate runway (months of survival at current burn rate)
    current_net_worth = net_worth_data[-1] if net_worth_data else 0
    runway = (current_net_worth / burn_rate) if burn_rate > 0 else 0
    
    # Calculate income trend (last 30 days vs previous 30 days)
    if len(income_data) >= 30:
        recent_income = sum(income_data[:30]) / 30
        previous_income = sum(income_data[30:60]) / 30 if len(income_data) >= 60 else recent_income
        income_trend = ((recent_income - previous_income) / previous_income * 100) if previous_income > 0 else 0
    else:
        income_trend = 0
    
    # Calculate expense trend
    if len(expense_data) >= 30:
        recent_expenses = sum(expense_data[:30]) / 30
        previous_expenses = sum(expense_data[30:60]) / 30 if len(expense_data) >= 60 else recent_expenses
        expense_trend = ((recent_expenses - previous_expenses) / previous_expenses * 100) if previous_expenses > 0 else 0
    else:
        expense_trend = 0
    
    # Calculate financial health score (0-100)
    health_score = 0
    
    # Savings rate component (30 points)
    if savings_rate >= 20:
        health_score += 30
    elif savings_rate >= 10:
        health_score += 20
    elif savings_rate >= 5:
        health_score += 10
    
    # Runway component (30 points)
    if runway >= 12:
        health_score += 30
    elif runway >= 6:
        health_score += 20
    elif runway >= 3:
        health_score += 10
    
    # Income stability component (20 points)
    income_variance = max(income_data) - min(income_data) if len(income_data) > 1 else 0
    if income_variance < avg_income * 0.2:
        health_score += 20
    elif income_variance < avg_income * 0.4:
        health_score += 10
    
    # Positive net worth component (20 points)
    if current_net_worth > 0:
        health_score += 20
    
    return {
        'has_data': True,
        'financial_health_score': round(health_score, 1),
        'savings_rate': round(savings_rate, 2),
        'burn_rate': round(burn_rate, 2),
        'runway_months': round(runway, 1),
        'income_trend': round(income_trend, 1),
        'expense_trend': round(expense_trend, 1),
        'current_net_worth': round(current_net_worth, 2),
        'avg_monthly_income': round(avg_income * 30, 2),
        'avg_monthly_expenses': round(avg_expenses * 30, 2),
        'avg_monthly_savings': round(avg_savings * 30, 2)
    }


# ── MONTHLY REPLAY ──
async def get_monthly_replay(db: AsyncSession, user_id: int, year: int = None, month: int = None) -> dict:
    """Get monthly replay data for historical review"""
    from datetime import date
    
    if not year or not month:
        today = date.today()
        year = today.year
        month = today.month
    
    # Get snapshots for the specified month
    snapshots = await list_snapshots(db, user_id, limit=1000)
    
    # Filter by month
    monthly_snapshots = [
        s for s in snapshots 
        if (s.log_date or s.timestamp.date()).year == year 
        and (s.log_date or s.timestamp.date()).month == month
    ]
    
    if len(monthly_snapshots) == 0:
        return {
            'has_data': False,
            'reason': 'No data for this month'
        }
    
    # Calculate monthly averages
    avg_vektra = sum(s.vektra_score for s in monthly_snapshots if s.vektra_score) / len([s for s in monthly_snapshots if s.vektra_score])
    avg_mood = sum(s.mood_score for s in monthly_snapshots if s.mood_score) / len([s for s in monthly_snapshots if s.mood_score])
    avg_energy = sum(s.energy_level for s in monthly_snapshots if s.energy_level) / len([s for s in monthly_snapshots if s.energy_level])
    avg_focus = sum(s.focus_hours for s in monthly_snapshots if s.focus_hours) / len([s for s in monthly_snapshots if s.focus_hours])
    
    # Calculate totals
    total_income = sum(s.daily_income for s in monthly_snapshots if s.daily_income)
    total_expenses = sum(s.expenses for s in monthly_snapshots if s.expenses)
    total_savings = sum(s.savings_investments for s in monthly_snapshots if s.savings_investments)
    
    # Find best and worst days
    best_day = max(monthly_snapshots, key=lambda s: s.vektra_score or 0)
    worst_day = min(monthly_snapshots, key=lambda s: s.vektra_score or 100)
    
    # Calculate improvement (first half vs second half)
    mid_point = len(monthly_snapshots) // 2
    first_half_avg = sum(s.vektra_score for s in monthly_snapshots[:mid_point] if s.vektra_score) / len([s for s in monthly_snapshots[:mid_point] if s.vektra_score])
    second_half_avg = sum(s.vektra_score for s in monthly_snapshots[mid_point:] if s.vektra_score) / len([s for s in monthly_snapshots[mid_point:] if s.vektra_score])
    improvement = second_half_avg - first_half_avg
    
    # Get key insights
    insights = []
    if improvement > 5:
        insights.append("Strong improvement throughout the month")
    elif improvement < -5:
        insights.append("Performance declined in second half of month")
    
    if avg_mood >= 7:
        insights.append("High mood maintained throughout month")
    elif avg_mood <= 4:
        insights.append("Low mood - consider mental health focus")
    
    if avg_focus >= 6:
        insights.append("Excellent focus hours achieved")
    
    return {
        'has_data': True,
        'year': year,
        'month': month,
        'days_logged': len(monthly_snapshots),
        'avg_vektra_score': round(avg_vektra, 1),
        'avg_mood': round(avg_mood, 1),
        'avg_energy': round(avg_energy, 1),
        'avg_focus_hours': round(avg_focus, 1),
        'total_income': round(total_income, 2),
        'total_expenses': round(total_expenses, 2),
        'total_savings': round(total_savings, 2),
        'best_day': {
            'date': best_day.log_date or best_day.timestamp.date(),
            'vektra_score': best_day.vektra_score,
            'mood_score': best_day.mood_score
        },
        'worst_day': {
            'date': worst_day.log_date or worst_day.timestamp.date(),
            'vektra_score': worst_day.vektra_score,
            'mood_score': worst_day.mood_score
        },
        'improvement': round(improvement, 1),
    }


async def export_user_data_csv(db: AsyncSession, user_id: int) -> str:
    """Export user snapshots as CSV string"""
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()
    
    if not snapshots:
        return "No data available for export"
    
    # Define CSV headers based on Snapshot model fields
    headers = [
        'timestamp', 'log_date', 'mood_score', 'energy_level', 'focus_level',
        'social_battery', 'health_battery', 'uncomfortable_moments',
        'daily_income', 'expenses', 'savings_investments', 'any_emergency',
        'tomorrow_goal', 'target_hit_bool', 'best_decision', 'worst_decision',
        'what_i_avoided', 'sleep_hours', 'screen_time', 'diet_taken',
        'skills_learned', 'new_ideas', 'gratitude_line', 'funny_line',
        'focus_hours', 'environment_rating', 'opportunity_cost',
        'vektra_score', 'burn_rate', 'survival_runway', 'leverage_score',
        'procrastination_delta', 'interactions_done'
    ]
    
    output = []
    output.append(','.join(headers))
    
    for snap in snapshots:
        row = []
        for field in headers:
            value = getattr(snap, field, None)
            if value is None:
                row.append('')
            elif isinstance(value, (datetime, date)):
                row.append(value.isoformat())
            elif isinstance(value, bool):
                row.append(str(value).lower())
            else:
                row.append(str(value))
        output.append(','.join(row))
    
    return '\n'.join(output)


async def export_user_data_json(db: AsyncSession, user_id: int) -> dict:
    """Export user snapshots as JSON dict"""
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()
    
    # Get user info
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    
    export_data = {
        'user': {
            'username': user.username if user else None,
            'email': user.email if user else None,
            'north_star': user.north_star if user else None,
            'primary_goal': user.primary_goal if user else None,
            'currency': user.currency if user else None,
        },
        'snapshots': [],
        'export_date': datetime.utcnow().isoformat(),
        'total_snapshots': len(snapshots)
    }
    
    for snap in snapshots:
        snapshot_dict = {
            'timestamp': snap.timestamp.isoformat() if snap.timestamp else None,
            'log_date': snap.log_date.isoformat() if snap.log_date else None,
            'mood_score': snap.mood_score,
            'energy_level': snap.energy_level,
            'focus_level': snap.focus_level,
            'social_battery': snap.social_battery,
            'health_battery': snap.health_battery,
            'uncomfortable_moments': snap.uncomfortable_moments,
            'daily_income': snap.daily_income,
            'expenses': snap.expenses,
            'savings_investments': snap.savings_investments,
            'any_emergency': snap.any_emergency,
            'tomorrow_goal': snap.tomorrow_goal,
            'target_hit_bool': snap.target_hit_bool,
            'best_decision': snap.best_decision,
            'worst_decision': snap.worst_decision,
            'what_i_avoided': snap.what_i_avoided,
            'sleep_hours': snap.sleep_hours,
            'screen_time': snap.screen_time,
            'diet_taken': snap.diet_taken,
            'skills_learned': snap.skills_learned,
            'new_ideas': snap.new_ideas,
            'gratitude_line': snap.gratitude_line,
            'funny_line': snap.funny_line,
            'focus_hours': snap.focus_hours,
            'environment_rating': snap.environment_rating,
            'opportunity_cost': snap.opportunity_cost,
            'vektra_score': snap.vektra_score,
            'burn_rate': snap.burn_rate,
            'survival_runway': snap.survival_runway,
            'leverage_score': snap.leverage_score,
            'procrastination_delta': snap.procrastination_delta,
            'interactions_done': snap.interactions_done,
        }
        export_data['snapshots'].append(snapshot_dict)
    
    return export_data
