import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "backend"))

from app.crud import create_snapshot, has_snapshot_for_date
from app.db.models import Base, User
from app.services.ai_client import AIClient
from app.services.report_service import build_weekly_summary
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def make_snapshot(**overrides):
    base = {
        "mood_score": 7,
        "energy_level": 8,
        "focus_level": 6,
        "social_battery": 7,
        "health_battery": 8,
        "sleep_hours": 7.5,
        "screen_time": 3,
        "focus_hours": 4,
        "daily_income": 100,
        "expenses": 40,
        "savings_investments": 20,
        "any_emergency": False,
        "vektra_score": 75,
        "leverage_score": 6,
        "tomorrow_goal": "Ship feature",
        "target_hit_bool": True,
        "procrastination_delta": 0,
        "survival_runway": 12,
        "current_capital": 600,
        "skills_learned": "Python",
        "new_ideas": "Test idea",
        "interactions_done": "Chat",
        "best_decision": "Worked on the report fix",
        "worst_decision": "Skipped a walk",
        "what_i_avoided": "Scrolling mindlessly",
        "funny_line": "The bug had a personality",
        "timestamp": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_build_weekly_summary_separates_entries_from_unique_days():
    snap_a = make_snapshot(timestamp=__import__("datetime").datetime(2026, 7, 1, 8, 0, 0))
    snap_b = make_snapshot(timestamp=__import__("datetime").datetime(2026, 7, 1, 20, 0, 0), target_hit_bool=False)
    snap_c = make_snapshot(timestamp=__import__("datetime").datetime(2026, 7, 2, 9, 0, 0))

    summary = await build_weekly_summary([snap_a, snap_b, snap_c])

    assert summary["days_logged"] == 3
    assert summary["unique_days_logged"] == 2
    assert summary["report_countdown"] == 5
    assert summary["signal_scores"]["Execution"] >= 0


@pytest.mark.asyncio
async def test_template_narrative_is_built_from_real_insights():
    import datetime as dt
    days = [
        # sleep lines up with score: long-sleep days score high, short-sleep days low
        make_snapshot(timestamp=dt.datetime(2026, 7, d, 9), sleep_hours=sleep, vektra_score=score,
                      daily_income=100, expenses=spend)
        for d, sleep, score, spend in [
            (1, 8.0, 80, 30), (2, 5.5, 55, 90), (3, 8.5, 82, 20), (4, 5.0, 50, 120),
            (5, 7.5, 76, 40), (6, 6.0, 58, 70),
        ]
    ]
    summary = await build_weekly_summary(days, period_days=7)
    insights = summary["insights"]

    assert insights["drivers"][0]["factor"] == "sleep_hours"
    assert insights["best_day"]["score"] == 82 and insights["worst_day"]["score"] == 50
    assert insights["money"]["net"] == 600 - 370

    narrative = AIClient().template_narrative(summary, "week")
    assert set(narrative) >= {"headline", "verdict", "story", "wins", "leaks", "patterns",
                              "money", "focus", "risk", "opportunity", "challenge"}
    assert "sleep" in narrative["patterns"][0]["detail"]
    assert "230" in narrative["money"]
    assert narrative["focus"]["title"] == "Protect your sleep"


@pytest.mark.asyncio
async def test_create_snapshot_reuses_existing_day_entry():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        user = User(username="dup", email="dup@example.com", password_hash="hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        first = await create_snapshot(session, user.id, {"mood_score": 5, "sleep_hours": 7, "timestamp": datetime(2026, 7, 8, 9, 0, 0)})
        second = await create_snapshot(session, user.id, {"mood_score": 8, "sleep_hours": 8, "timestamp": datetime(2026, 7, 8, 18, 0, 0)})

        assert first.id == second.id
        assert second.mood_score == 5
        assert getattr(second, "is_duplicate", False) is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_weekly_summary_marks_report_not_ready_until_three_unique_days():
    def make_snapshot(day: int):
        return SimpleNamespace(
            timestamp=datetime(2026, 7, day, 9, 0, 0),
            mood_score=7,
            energy_level=6,
            focus_level=6,
            social_battery=7,
            health_battery=6,
            sleep_hours=7,
            screen_time=3,
            focus_hours=4,
            daily_income=100,
            expenses=50,
            savings_investments=20,
            any_emergency=None,
            tomorrow_goal='Ship the feature',
            target_hit_bool=True,
            procrastination_delta=0,
            survival_runway=20,
            current_capital=1000,
            skills_learned='A lesson',
            new_ideas=None,
            interactions_done=None,
            best_decision='Stayed focused',
            worst_decision=None,
            what_i_avoided=None,
            funny_line=None,
            vektra_score=70,
            leverage_score=5,
        )

    summary = await build_weekly_summary([make_snapshot(1), make_snapshot(2)])
    assert summary['report_ready'] is False
    assert '3' in summary['report_readiness_message']


@pytest.mark.asyncio
async def test_has_snapshot_for_date_detects_existing_day_entry():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        user = User(username="check", email="check@example.com", password_hash="hash")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert not await has_snapshot_for_date(session, user.id, datetime(2026, 7, 8).date())
        await create_snapshot(session, user.id, {"mood_score": 6, "sleep_hours": 7, "timestamp": datetime(2026, 7, 8, 9, 0, 0)})
        assert await has_snapshot_for_date(session, user.id, datetime(2026, 7, 8).date())

    await engine.dispose()


@pytest.mark.asyncio
async def test_report_score_uses_signal_breakdown_average():
    snapshot = make_snapshot(timestamp=__import__("datetime").datetime(2026, 7, 1, 8, 0, 0))
    summary = await build_weekly_summary([snapshot])

    assert "report_score" in summary
    assert summary["report_score"] >= 70
    expected = round(
        summary["signal_scores"]["Financial"] * 0.25
        + summary["signal_scores"]["Mental"] * 0.2
        + summary["signal_scores"]["Execution"] * 0.2
        + summary["signal_scores"]["Body"] * 0.2
        + summary["signal_scores"]["Growth"] * 0.15,
        1,
    )
    assert expected == summary["report_score"]
