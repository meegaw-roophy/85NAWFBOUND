from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.services.ai_client import ai_client
import datetime


async def generate_and_store_report(db: AsyncSession, user_id: int, period_start=None, period_end=None):
    snaps = await crud.list_snapshots(db, user_id, limit=200)
    if period_start or period_end:
        snaps = [s for s in snaps if (not period_start or s.timestamp >= period_start) and (not period_end or s.timestamp <= period_end)]

    count = len(snaps)
    moods = [s.mood for s in snaps if s.mood is not None]
    avg_mood = round(sum(moods) / len(moods), 2) if moods else None

    range_start = period_start or (snaps[-1].timestamp if snaps else None)
    range_end = period_end or (snaps[0].timestamp if snaps else None)
    summary = {
        "snapshot_count": count,
        "average_mood": avg_mood,
        "period_start": range_start.isoformat() if range_start else None,
        "period_end": range_end.isoformat() if range_end else None,
        "generated_at": datetime.datetime.utcnow().isoformat(),
    }

    content = {
        "snapshots": [
            {
                "id": s.id,
                "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                "mood": s.mood,
                "income": s.income,
                "expenses": s.expenses,
            }
            for s in snaps
        ],
        "summary": summary,
    }

    summary_text = (
        f"Generated {count} snapshot summary for {range_start.date() if range_start else 'N/A'} to {range_end.date() if range_end else 'N/A'}. "
        f"Average mood: {avg_mood}."
    )

    if count:
        ai_summary = await ai_client.summarize_snapshots(
            [
                {
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "mood": s.mood,
                    "income": s.income,
                    "expenses": s.expenses,
                    "focus": s.focus,
                    "energy": s.energy,
                }
                for s in snaps
            ],
            period_start=range_start,
            period_end=range_end,
        )
        summary_text = ai_summary or summary_text

    report_payload = {
        "period_start": period_start,
        "period_end": period_end,
        "content": content,
        "summary_text": summary_text,
    }
    rpt = await crud.create_report(db, user_id, report_payload)
    return rpt
