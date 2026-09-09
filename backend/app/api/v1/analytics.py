"""
Landing Page Analytics
=======================
Lightweight, first-party click tracking for the landing page CTAs, so we
don't depend on an ad platform's own click count. Recording is public
(anonymous visitors, no login yet) and reading is admin-only.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import User, LandingClick
from app.api.v1.admin import require_admin

router = APIRouter()


class LandingClickIn(BaseModel):
    link: str
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


@router.post("/landing-click", status_code=204)
async def record_landing_click(
    payload: LandingClickIn,
    db: AsyncSession = Depends(get_session)
):
    """Record a single click on a landing-page CTA. Fire-and-forget, no auth."""
    click = LandingClick(
        link=payload.link[:100],
        referrer=payload.referrer[:500] if payload.referrer else None,
        utm_source=payload.utm_source[:100] if payload.utm_source else None,
        utm_medium=payload.utm_medium[:100] if payload.utm_medium else None,
        utm_campaign=payload.utm_campaign[:100] if payload.utm_campaign else None,
    )
    db.add(click)
    await db.commit()
    return None


class LinkBreakdown(BaseModel):
    link: str
    count: int


class LandingClickStats(BaseModel):
    total: int
    last_24h: int
    by_link_24h: List[LinkBreakdown]


@router.get("/landing-clicks", response_model=LandingClickStats)
async def get_landing_click_stats(
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: total and last-24h landing page CTA click counts."""
    since = datetime.utcnow() - timedelta(hours=24)

    total = (await db.execute(select(func.count(LandingClick.id)))).scalar() or 0

    last_24h = (await db.execute(
        select(func.count(LandingClick.id)).where(LandingClick.created_at >= since)
    )).scalar() or 0

    breakdown_rows = await db.execute(
        select(LandingClick.link, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since)
        .group_by(LandingClick.link)
        .order_by(func.count(LandingClick.id).desc())
    )

    return LandingClickStats(
        total=total,
        last_24h=last_24h,
        by_link_24h=[LinkBreakdown(link=link, count=count) for link, count in breakdown_rows.all()]
    )
