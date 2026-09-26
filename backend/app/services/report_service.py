"""
VEKTRA Report Service
=====================
Generates weekly, monthly, quarterly and annual reports.
Pulls snapshots, computes summaries, calls AI, stores report.
"""

import datetime
import os
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import crud
from app.db.models import Snapshot, User, Report
from app.services.ai_client import ai_client


def _safe_avg(values: list) -> Optional[float]:
    """Return rounded average or None if list is empty."""
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else None


def _safe_sum(values: list) -> float:
    """Return sum of non-None values."""
    return round(sum(v for v in values if v is not None), 2)


def _safe_list(values: list, limit: int = 3) -> list:
    """Return non-None, non-empty string values up to limit."""
    return [v for v in values if v and len(str(v)) > 3][:limit]


async def build_weekly_summary(snapshots: List[Snapshot], period_days: int = 7) -> dict:
    """
    Compute period summary statistics from a list of snapshots (used for
    both weekly and monthly reports - period_days controls the "X/N days
    logged" framing and readiness threshold). This is what gets sent to the
    AI and stored in the report.
    """
    if not snapshots:
        return {}

    # ── Mental averages ──────────────────────
    avg_mood         = _safe_avg([s.mood_score for s in snapshots])
    avg_energy       = _safe_avg([s.energy_level for s in snapshots])
    avg_focus        = _safe_avg([s.focus_level for s in snapshots])
    avg_social       = _safe_avg([s.social_battery for s in snapshots])
    avg_health       = _safe_avg([s.health_battery for s in snapshots])

    # ── Body averages ────────────────────────
    avg_sleep        = _safe_avg([s.sleep_hours for s in snapshots])
    avg_screen       = _safe_avg([s.screen_time for s in snapshots])
    avg_focus_hours  = _safe_avg([s.focus_hours for s in snapshots])

    # ── Financial totals ─────────────────────
    total_income     = _safe_sum([s.daily_income for s in snapshots])
    total_expenses   = _safe_sum([s.expenses for s in snapshots])
    total_savings    = _safe_sum([s.savings_investments for s in snapshots])
    net_cash_flow    = round(total_income - total_expenses, 2)
    emergency_count  = sum(1 for s in snapshots if s.any_emergency)

    # ── VEKTRA score ─────────────────────────
    avg_vektra_score = _safe_avg([s.vektra_score for s in snapshots])
    avg_leverage     = _safe_avg([s.leverage_score for s in snapshots])

    # ── Execution stats ──────────────────────
    goals_set        = sum(1 for s in snapshots if s.tomorrow_goal)
    goals_hit        = sum(1 for s in snapshots if s.target_hit_bool is True)
    goal_hit_rate    = round(goals_hit / goals_set * 100, 1) if goals_set > 0 else None
    procrast_days    = sum(1 for s in snapshots if s.procrastination_delta and s.procrastination_delta > 0)

    # ── Survival runway (latest snapshot) ────
    latest = sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[0]
    survival_runway  = latest.survival_runway

    # ── Growth counts ────────────────────────
    skills_count     = sum(1 for s in snapshots if s.skills_learned)
    ideas_count      = sum(1 for s in snapshots if s.new_ideas)
    interactions_count = sum(1 for s in snapshots if s.interactions_done)

    # ── Qualitative highlights ────────────────
    best_decisions   = _safe_list([s.best_decision for s in snapshots])
    worst_decisions  = _safe_list([s.worst_decision for s in snapshots])
    avoided_items    = _safe_list([s.what_i_avoided for s in snapshots])
    funny_lines      = _safe_list([s.funny_line for s in snapshots])

    snapshot_dates = {
        s.timestamp.date() for s in snapshots if getattr(s, 'timestamp', None) is not None
    }
    unique_days_logged = len(snapshot_dates) or len(snapshots)
    # 3 days is enough to say something meaningful about a week; longer
    # periods deserve more data before claiming to summarize them.
    minimum_days_for_report = 3 if period_days <= 7 else 7 if period_days <= 30 else 14
    report_ready = unique_days_logged >= minimum_days_for_report
    report_countdown = max(0, period_days - unique_days_logged)
    days_needed = max(0, minimum_days_for_report - unique_days_logged)
    period_label = 'week' if period_days <= 7 else 'quarter' if period_days > 60 else 'month'
    report_readiness_message = (
        f'Enough data for a meaningful {period_label}ly report.'
        if report_ready
        else f'Need {days_needed} more day{"s" if days_needed != 1 else ""} to reach {minimum_days_for_report} logged days for a richer {period_label}ly report.'
    )
    component_scores = {
        'Financial': round(min(100, max(0, avg_vektra_score or 50))),
        'Mental': round(min(100, max(0, (avg_mood or 0) * 10))),
        'Execution': round(min(100, max(0, goal_hit_rate or 0))),
        'Body': round(min(100, max(0, (avg_sleep and avg_sleep / 9 * 100) or 0))),
        'Growth': round(min(100, max(0, (skills_count / 7) * 100 if skills_count else 0))),
    }
    signal_scores = {
        'Financial': component_scores['Financial'],
        'Mental': component_scores['Mental'],
        'Execution': component_scores['Execution'],
        'Body': component_scores['Body'],
        'Growth': component_scores['Growth'],
    }
    report_score = round(
        (
            signal_scores['Financial'] * 0.25
            + signal_scores['Mental'] * 0.2
            + signal_scores['Execution'] * 0.2
            + signal_scores['Body'] * 0.2
            + signal_scores['Growth'] * 0.15
        ),
        1,
    )

    return {
        'days_logged':          len(snapshots),
        'unique_days_logged':   unique_days_logged,
        'report_ready':         report_ready,
        'report_readiness_message': report_readiness_message,
        'report_countdown':     report_countdown,
        'signal_scores':        signal_scores,
        'report_score':         report_score,
        'avg_vektra_score':     avg_vektra_score,
        'avg_mood':             avg_mood,
        'avg_energy':           avg_energy,
        'avg_focus':            avg_focus,
        'avg_social':           avg_social,
        'avg_health':           avg_health,
        'avg_sleep':            avg_sleep,
        'avg_screen_time':      avg_screen,
        'avg_focus_hours':      avg_focus_hours,
        'total_income':         total_income,
        'total_expenses':       total_expenses,
        'total_savings':        total_savings,
        'net_cash_flow':        net_cash_flow,
        'emergency_count':      emergency_count,
        'goals_set':            goals_set,
        'goals_hit':            goals_hit,
        'goal_hit_rate':        round(goals_hit / goals_set * 100, 1) if goals_set > 0 else None,
        'procrastination_days': procrast_days,
        'avg_leverage':         avg_leverage,
        'survival_runway':      survival_runway,
        'skills_count':         skills_count,
        'ideas_count':          ideas_count,
        'interactions_count':   interactions_count,
        'best_decisions':       best_decisions,
        'worst_decisions':      worst_decisions,
        'avoided_items':        avoided_items,
        'funny_lines':          funny_lines,
    }


async def generate_period_report(
    db: AsyncSession,
    user_id: int,
    report_type: str,
    period_days: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    """
    Full period report pipeline, shared by weekly (period_days=7) and
    monthly (period_days=30) reports:
    1. Pull last period_days of snapshots
    2. Build summary statistics
    3. Get user context (north star, tone preference)
    4. Pull historical reports of the SAME report_type for AI memory
       (monthly compares against past months, not past weeks)
    5. Call AI to generate narrative with historical context
    6. Store report in database
    7. Return report object
    """
    period_label = 'week' if period_days <= 7 else 'quarter' if period_days > 60 else 'month'

    # ── Default to the last period_days ──────
    if not period_end:
        period_end = datetime.datetime.utcnow()
    if not period_start:
        period_start = period_end - datetime.timedelta(days=period_days)

    # ── Pull snapshots ───────────────────────
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .where(Snapshot.timestamp >= period_start)
        .where(Snapshot.timestamp <= period_end)
        .order_by(Snapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()

    # ── Pull user context ────────────────────
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    user_data = {
        'north_star': user.north_star if user else None,
        'primary_goal': user.primary_goal if user else None,
        'feedback_tone': user.preferred_feedback_tone if user else 'Balanced',
        'language': user.language if user else None,
    }

    # ── Build period summary ─────────────────
    summary = await build_weekly_summary(snapshots, period_days=period_days)

    # ── Pull historical reports of the same type for AI Memory ──
    historical_result = await db.execute(
        select(Report)
        .where(Report.user_id == user_id)
        .where(Report.report_type == report_type)
        .where(Report.status == 'ready')
        .order_by(Report.generated_at.desc())
        .limit(4)  # Last 4 periods for context
    )
    historical_reports = historical_result.scalars().all()

    # Build historical context
    historical_context = []
    for report in historical_reports:
        if report.content:
            historical_context.append({
                'period_start': report.period_start.isoformat() if report.period_start else None,
                'period_end': report.period_end.isoformat() if report.period_end else None,
                'vektra_score': report.vektra_score,
                'summary': report.content.get('avg_vektra_score'),
                'mood': report.content.get('avg_mood'),
                'sleep': report.content.get('avg_sleep'),
                'net_cash_flow': report.content.get('net_cash_flow'),
                'goal_hit_rate': report.content.get('goal_hit_rate'),
            })

    # ── Generate AI narrative with memory ───────
    summary_text = await ai_client.generate_weekly_report(
        user_data=user_data,
        weekly_summary=summary,
        feedback_tone=user_data.get('feedback_tone', 'Balanced'),
        historical_context=historical_context,
        period_days=period_days,
        period_label=period_label,
    )

    # ── Calculate headline report score ─────
    avg_score = summary.get('report_score', summary.get('avg_vektra_score'))

    # ── Store report ──────────────────────────
    report_payload = {
        'period_start':  period_start,
        'period_end':    period_end,
        'report_type':   report_type,
        'status':        'ready',
        'summary_text':  summary_text,
        'vektra_score':  avg_score,
        'content':       summary,
        'delivered':     False,
        'opened':        False,
    }
    report = await crud.create_report(db, user_id, report_payload)
    return report


async def generate_weekly_report(
    db: AsyncSession,
    user_id: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    return await generate_period_report(db, user_id, 'weekly', 7, period_start, period_end)


async def generate_monthly_report(
    db: AsyncSession,
    user_id: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    return await generate_period_report(db, user_id, 'monthly', 30, period_start, period_end)


async def generate_quarterly_report(
    db: AsyncSession,
    user_id: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    return await generate_period_report(db, user_id, 'quarterly', 90, period_start, period_end)


async def generate_weekly_preview(
    db: AsyncSession,
    user_id: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    """
    Free-tier weekly report: the real computed scores (that's the core
    "know your trajectory" hook, not something to paywall), but no AI
    narrative - just an upgrade teaser instead of the wins/killers/
    directive breakdown. Zero AI cost, matches the pricing page's actual
    promise of "one weekly preview report" for Free.
    """
    period_days = 7
    if not period_end:
        period_end = datetime.datetime.utcnow()
    if not period_start:
        period_start = period_end - datetime.timedelta(days=period_days)

    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .where(Snapshot.timestamp >= period_start)
        .where(Snapshot.timestamp <= period_end)
        .order_by(Snapshot.timestamp.desc())
    )
    snapshots = result.scalars().all()
    summary = await build_weekly_summary(snapshots, period_days=period_days)

    if summary.get('report_ready'):
        teaser = (
            "🔒 This is a preview. Your full weekly breakdown — wins, the one metric "
            "quietly holding you back, and a direct action plan generated fresh from "
            "your own data — unlocks on Vector and above."
        )
    else:
        teaser = summary.get(
            'report_readiness_message',
            'Log a few more days to unlock your weekly preview.',
        )

    report_payload = {
        'period_start':  period_start,
        'period_end':    period_end,
        'report_type':   'weekly',
        'status':        'ready',
        'summary_text':  teaser,
        'vektra_score':  summary.get('report_score', summary.get('avg_vektra_score')),
        'content':       summary,
        'delivered':     False,
        'opened':        False,
    }
    return await crud.create_report(db, user_id, report_payload)


async def generate_daily_report(db: AsyncSession, user_id: int, user_tier: str = 'free') -> object:
    """
    Short AI-personalized narrative for today's single snapshot. Paid tiers get
    the real AI call; free tier gets the same zero-cost mock text the AI client
    already falls back to when Claude itself is unavailable - enforced here
    server-side (not just hidden behind a frontend check) so a free user can't
    get a paid AI call for free by hitting the endpoint directly.
    """
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(1)
    )
    snap = result.scalars().first()
    if not snap:
        report_payload = {
            'report_type':  'daily',
            'status':       'ready',
            'summary_text': 'No log found for today. Submit your daily log first.',
            'content':      {},
        }
        return await crud.create_report(db, user_id, report_payload)

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    user_data = {
        'north_star': user.north_star if user else None,
        'feedback_tone': user.preferred_feedback_tone if user else 'Balanced',
        'language': user.language if user else None,
    }

    cashflow = None
    if snap.daily_income is not None and snap.expenses is not None:
        cashflow = snap.daily_income - snap.expenses

    daily_snapshot = {
        'vektra_score':  snap.vektra_score,
        'mood_score':    snap.mood_score,
        'energy_level':  snap.energy_level,
        'sleep_hours':   snap.sleep_hours,
        'cashflow':      cashflow,
        'goal_hit':      snap.target_hit_bool,
        'best_decision': snap.best_decision,
        'tomorrow_goal': snap.tomorrow_goal,
    }

    summary_text = await ai_client.generate_daily_report(
        user_data=user_data,
        daily_snapshot=daily_snapshot,
        feedback_tone=user_data.get('feedback_tone', 'Balanced'),
        force_mock=(user_tier == 'free'),
    )

    report_payload = {
        'period_start':  snap.timestamp,
        'period_end':    snap.timestamp,
        'report_type':   'daily',
        'status':        'ready',
        'summary_text':  summary_text,
        'vektra_score':  snap.vektra_score,
        'content':       daily_snapshot,
    }
    return await crud.create_report(db, user_id, report_payload)


async def generate_and_store_report(
    db: AsyncSession,
    user_id: int,
    report_type: str = 'weekly',
    period_start=None,
    period_end=None,
    user_tier: str = 'free',
) -> object:
    """
    Tier matrix (matches the pricing page's advertised features exactly):
      Free:  daily = template mock, weekly = preview (no AI), no monthly/quarterly
      Vector (tier1): daily/weekly get the real AI call, no monthly/quarterly
      Apex/Founder (tier2/tier3): everything Vector has, plus monthly/quarterly

    Monthly/quarterly access is enforced by the caller (reports.py) with an
    explicit 403 before this ever runs, since "you don't have this" deserves
    a clear rejection rather than a silent downgrade. Daily/weekly downgrade
    gracefully instead, since Free is meant to get *something* for both.
    """
    if report_type == 'daily':
        return await generate_daily_report(db, user_id, user_tier=user_tier)
    if report_type == 'monthly':
        return await generate_monthly_report(db, user_id, period_start, period_end)
    if report_type == 'quarterly':
        return await generate_quarterly_report(db, user_id, period_start, period_end)
    if user_tier == 'free':
        return await generate_weekly_preview(db, user_id, period_start, period_end)
    return await generate_weekly_report(db, user_id, period_start, period_end)
