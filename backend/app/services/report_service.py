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
from sqlalchemy import func, select

from app import crud
from app.db.models import Snapshot, User, Report
from app.services.ai_client import ai_client, render_narrative_text
from app.services.report_insights import ENGINE_WEIGHTS, build_insights


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


PERIODS = {'weekly': (7, 'week'), 'monthly': (30, 'month'), 'quarterly': (90, 'quarter')}

# Percentiles only mean something once enough people are in the pool.
MIN_PERCENTILE_POOL = 20


async def build_weekly_summary(
    snapshots: List[Snapshot],
    period_days: int = 7,
    previous_snapshots: Optional[List[Snapshot]] = None,
) -> dict:
    """
    Compute period summary statistics from a list of snapshots (weekly,
    monthly or quarterly - period_days controls the "X/N days logged"
    framing and readiness threshold). The raw totals stay at the top level
    for older readers; the deeper analysis lives under 'insights'.
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
    # Unknown (None), not 0, until capital is logged: the engine scores missing
    # capital as zero runway, which the narrative then reported as "broke".
    latest = sorted(snapshots, key=lambda s: s.timestamp, reverse=True)[0]
    capital_logged   = any(s.current_capital is not None for s in snapshots)
    survival_runway  = latest.survival_runway if capital_logged else None

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

    # Engine scores are each day's real engine score (the same engine as the
    # dashboard) averaged over the days the user logged that area. They used
    # to be stand-ins - "Financial" was the overall score, "Growth" counted
    # skills out of 7 regardless of period length.
    insights = build_insights(snapshots, previous_snapshots, period_days)
    signal_scores = {name: (insights.get('engines') or {}).get(name, {}).get('score') for name in ENGINE_WEIGHTS}
    # Same number the "vs last period" comparison uses, so the two always agree.
    report_score = (insights.get('current') or {}).get('score')
    if report_score is None:
        report_score = avg_vektra_score

    return {
        'days_logged':          len(snapshots),
        'unique_days_logged':   unique_days_logged,
        'report_ready':         report_ready,
        'report_readiness_message': report_readiness_message,
        'report_countdown':     report_countdown,
        'signal_scores':        signal_scores,
        'report_score':         report_score,
        'insights':             insights,
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
        'goal_hit_rate':        goal_hit_rate,
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


async def _snapshots_between(db: AsyncSession, user_id: int, start, end) -> List[Snapshot]:
    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .where(Snapshot.timestamp >= start)
        .where(Snapshot.timestamp <= end)
        .order_by(Snapshot.timestamp.desc())
    )
    return result.scalars().all()


async def score_percentile(db: AsyncSession, user_id: int, report_type: str, score, since) -> Optional[dict]:
    """Share of other users whose latest report of this type scored below this one."""
    if score is None:
        return None
    result = await db.execute(
        select(Report.user_id, Report.vektra_score, Report.generated_at)
        .where(Report.report_type == report_type)
        .where(Report.status == 'ready')
        .where(Report.generated_at >= since)
        .where(Report.vektra_score.is_not(None))
        .order_by(Report.generated_at)
    )
    latest = {uid: s for uid, s, _ in result.all() if uid != user_id}
    if len(latest) < MIN_PERCENTILE_POOL:
        return None
    below = sum(1 for s in latest.values() if s < score)
    return {'better_than_pct': round(below / len(latest) * 100), 'pool': len(latest)}


async def generate_period_report(
    db: AsyncSession,
    user_id: int,
    report_type: str,
    period_start: Optional[datetime.datetime] = None,
    period_end: Optional[datetime.datetime] = None,
    full_access: bool = True,
) -> object:
    """
    Full period report pipeline, shared by weekly, monthly and quarterly:
    1. Pull this period's snapshots, and the period before it for comparison
    2. Compute the summary and insights (report_insights.py)
    3. Pull the last few reports of the SAME type for the AI's memory
    4. Write the narrative (Claude for paid tiers, the template otherwise)
    5. Store and return the report

    full_access=False is the free weekly preview: real scores, engines and
    the headline insight, with the deeper sections marked locked and no AI
    cost.
    """
    period_days, period_label = PERIODS[report_type]

    if not period_end:
        period_end = datetime.datetime.utcnow()
    if not period_start:
        period_start = period_end - datetime.timedelta(days=period_days)

    snapshots = await _snapshots_between(db, user_id, period_start, period_end)
    previous = await _snapshots_between(
        db, user_id, period_start - datetime.timedelta(days=period_days), period_start
    )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()
    user_data = {
        'north_star': user.north_star if user else None,
        'primary_goal': user.primary_goal if user else None,
        'feedback_tone': user.preferred_feedback_tone if user else 'Balanced',
        'language': user.language if user else None,
        'currency': user.currency if user else None,
    }

    summary = await build_weekly_summary(snapshots, period_days=period_days, previous_snapshots=previous)
    summary['access'] = 'full' if full_access else 'preview'
    summary['latest_snapshot_id'] = (await db.execute(
        select(func.max(Snapshot.id)).where(Snapshot.user_id == user_id)
    )).scalar()

    if summary.get('report_ready'):
        historical_result = await db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .where(Report.report_type == report_type)
            .where(Report.status == 'ready')
            .order_by(Report.generated_at.desc())
            .limit(4)
        )
        historical_context = [
            {
                'period_end': r.period_end.isoformat() if r.period_end else None,
                'score': r.vektra_score,
                'mood': (r.content or {}).get('avg_mood'),
                'sleep': (r.content or {}).get('avg_sleep'),
                'net_cash_flow': (r.content or {}).get('net_cash_flow'),
                'goal_hit_rate': (r.content or {}).get('goal_hit_rate'),
            }
            for r in historical_result.scalars().all() if r.content
        ]

        written = await ai_client.generate_period_narrative(
            user_data=user_data,
            summary=summary,
            period_label=period_label,
            historical_context=historical_context,
            force_template=not full_access,
        )
        narrative = written['narrative']
        summary['narrative_source'] = written['source']
        summary['percentile'] = await score_percentile(
            db, user_id, report_type, summary.get('report_score'),
            since=period_end - datetime.timedelta(days=period_days * 2),
        )

        if full_access:
            summary['narrative'] = narrative
            summary_text = render_narrative_text(narrative)
        else:
            summary['narrative'] = {
                'headline': narrative['headline'],
                'verdict': narrative['verdict'],
                'story': narrative['story'],
                'patterns': narrative['patterns'][:1],
            }
            summary['locked_sections'] = ['wins', 'leaks', 'money', 'plan']
            summary_text = (
                f"🎯 {narrative['headline']}\n\n{narrative['story']}\n\n"
                "🔒 Your full breakdown (what went right, what's quietly costing you, "
                "every pattern in your data, your money read and a 3-step plan) unlocks on Vector and above."
            )
    else:
        summary_text = summary.get(
            'report_readiness_message', f'Log a few more days to unlock your {period_label}ly report.'
        ) if summary else f'No logs in this {period_label} yet. Log today to start your report.'

    report_payload = {
        'period_start':  period_start,
        'period_end':    period_end,
        'report_type':   report_type,
        'status':        'ready',
        'summary_text':  summary_text,
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
    full_access = user_tier != 'free'
    return await generate_period_report(
        db, user_id, report_type if report_type in PERIODS else 'weekly',
        period_start, period_end, full_access=full_access,
    )
