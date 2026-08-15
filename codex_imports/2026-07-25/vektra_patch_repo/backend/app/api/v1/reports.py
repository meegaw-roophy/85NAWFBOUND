import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from app.schemas import ReportCreate, ReportOut
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app import crud
from app.core.deps import get_current_user
from app.db.models import Snapshot
from app.services.report_service import generate_and_store_report

router = APIRouter()


def _snapshot_day(snapshot: Snapshot) -> Optional[datetime.date]:
    if snapshot.log_date:
        return snapshot.log_date
    if snapshot.timestamp:
        return snapshot.timestamp.date()
    return None


def _pct_score(value, fallback=50):
    if value is None:
        return fallback
    return max(0, min(100, round(value)))


def _build_daily_summary_response(snapshot: Snapshot) -> dict:
    income = snapshot.daily_income or 0
    expenses = snapshot.expenses or 0
    cash_flow = income - expenses
    score = _pct_score(snapshot.vektra_score)
    mood = snapshot.mood_score
    energy = snapshot.energy_level
    focus_hours = snapshot.focus_hours or 0
    screen_time = snapshot.screen_time or 0
    sleep = snapshot.sleep_hours or 0
    goal_text = "hit" if snapshot.target_hit_bool is True else "missed" if snapshot.target_hit_bool is False else "unclear"

    if score >= 75:
        trajectory = "Rising"
    elif score >= 55:
        trajectory = "Steady"
    elif score >= 40:
        trajectory = "Stalling"
    else:
        trajectory = "Needs reset"

    leak = "No major leak detected yet. Keep tightening the log."
    if sleep and sleep < 6.5:
        leak = f"Sleep is the leak: {sleep:.1f}h will tax focus tomorrow."
    elif screen_time and focus_hours and screen_time > focus_hours:
        leak = f"Attention leak: {screen_time:.1f}h screen time beat {focus_hours:.1f}h focus."
    elif cash_flow < 0:
        leak = f"Cash leak: daily flow closed at {cash_flow:+.0f}."
    elif snapshot.target_hit_bool is False:
        leak = "Execution leak: yesterday's target was missed."

    best = snapshot.best_decision or "No best decision logged."
    tomorrow = snapshot.tomorrow_goal or "Set one clear target before the day ends."

    summary_text = "\n".join([
        f"TRAJECTORY: {trajectory} at {score}/100.",
        f"MENTAL: mood {mood or '-'} /10, energy {energy or '-'} /10.",
        f"BODY: sleep {sleep:.1f}h." if sleep else "BODY: sleep not logged.",
        f"FINANCE: cash flow {cash_flow:+.0f}.",
        f"EXECUTION: yesterday's target was {goal_text}.",
        f"BEST MOVE: {best}",
        f"LEAK: {leak}",
        f"TOMORROW: {tomorrow}",
    ])

    return {
        "has_snapshot": True,
        "date": _snapshot_day(snapshot).isoformat() if _snapshot_day(snapshot) else None,
        "score": score,
        "cash_flow": round(cash_flow, 2),
        "goal_status": goal_text,
        "summary_text": summary_text,
        "signal_scores": {
            "Financial": score,
            "Mental": _pct_score((mood or 0) * 10, fallback=0),
            "Execution": 100 if snapshot.target_hit_bool is True else 35 if snapshot.target_hit_bool is False else 50,
            "Body": _pct_score((sleep / 9) * 100, fallback=0) if sleep else 0,
            "Growth": 80 if snapshot.skills_learned else 30,
        },
    }


@router.get("/users/{user_id}/reports/daily-summary")
async def get_daily_summary(
    user_id: int,
    target_date: Optional[datetime.date] = Query(default=None, alias="date"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    result = await db.execute(
        select(Snapshot)
        .where(Snapshot.user_id == user_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(30)
    )
    snapshots = result.scalars().all()
    snapshot = None
    if target_date:
        snapshot = next((s for s in snapshots if _snapshot_day(s) == target_date), None)
    elif snapshots:
        snapshot = snapshots[0]

    if not snapshot:
        return {
            "has_snapshot": False,
            "date": target_date.isoformat() if target_date else None,
            "summary_text": "No daily log found. Submit today's log first.",
        }
    return _build_daily_summary_response(snapshot)


@router.post("/users/{user_id}/reports", response_model=ReportOut)
async def create_report(user_id: int, payload: ReportCreate, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    rpt = await crud.create_report(db, user_id, payload.dict(exclude_none=True))
    return rpt


@router.get("/users/{user_id}/reports", response_model=List[ReportOut])
async def list_reports(user_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return await crud.list_reports(db, user_id)


@router.post("/users/{user_id}/reports/generate", response_model=ReportOut)
async def generate_report(user_id: int, payload: Optional[ReportCreate] = None, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    period_start = payload.period_start if payload else None
    period_end = payload.period_end if payload else None
    rpt = await generate_and_store_report(db, user_id, period_start=period_start, period_end=period_end)
    return rpt


@router.get("/users/{user_id}/reports/{report_id}", response_model=ReportOut)
async def get_report(user_id: int, report_id: int, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    report = await crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    return report
