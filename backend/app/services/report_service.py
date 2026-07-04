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
from app.db.models import Snapshot, User
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


async def build_weekly_summary(snapshots: List[Snapshot]) -> dict:
    """
    Compute weekly summary statistics from a list of snapshots.
    This is what gets sent to the AI and stored in the report.
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

    return {
        'days_logged':          len(snapshots),
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


async def generate_weekly_report(
    db: AsyncSession,
    user_id: int,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
) -> object:
    """
    Full weekly report pipeline:
    1. Pull last 7 days of snapshots
    2. Build summary statistics
    3. Get user context (north star, tone preference)
    4. Call AI to generate narrative
    5. Store report in database
    6. Return report object
    """
    # ── Default to last 7 days ───────────────
    if not period_end:
        period_end = datetime.datetime.utcnow()
    if not period_start:
        period_start = period_end - datetime.timedelta(days=7)

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
    }

    # ── Build weekly summary ─────────────────
    summary = await build_weekly_summary(snapshots)

    # ── Generate AI narrative ─────────────────
    summary_text = await ai_client.generate_weekly_report(
        user_data=user_data,
        weekly_summary=summary,
        feedback_tone=user_data.get('feedback_tone', 'Balanced'),
    )

    # ── Calculate average vektra score ───────
    avg_score = summary.get('avg_vektra_score')

    # ── Store report ──────────────────────────
    report_payload = {
        'period_start':  period_start,
        'period_end':    period_end,
        'report_type':   'weekly',
        'status':        'ready',
        'summary_text':  summary_text,
        'vektra_score':  avg_score,
        'content':       summary,
        'delivered':     False,
        'opened':        False,
    }
    report = await crud.create_report(db, user_id, report_payload)
    return report


async def generate_and_store_report(
    db: AsyncSession,
    user_id: int,
    period_start=None,
    period_end=None,
) -> object:
    return await generate_weekly_report(db, user_id, period_start, period_end)
