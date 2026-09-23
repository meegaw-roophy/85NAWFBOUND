"""
Landing Page Analytics
=======================
Lightweight, first-party click tracking for the landing page CTAs, so we
don't depend on an ad platform's own click count (or a link shortener's
free-tier click cap). Recording is public (anonymous visitors, no login
yet) and reading is admin-only.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import httpx

from app.db.session import get_session
from app.db.models import User, LandingClick
from app.api.v1.admin import require_admin

router = APIRouter()


def parse_user_agent(ua: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Lightweight User-Agent parsing - device type, OS, browser. No external
    dependency or network call, so unlike geolocation this is 100% reliable
    and free regardless of click volume.
    """
    if not ua:
        return None, None, None
    ua_l = ua.lower()

    if 'ipad' in ua_l or 'tablet' in ua_l or ('android' in ua_l and 'mobile' not in ua_l):
        device_type = 'Tablet'
    elif 'mobile' in ua_l or 'iphone' in ua_l or 'android' in ua_l:
        device_type = 'Mobile'
    else:
        device_type = 'Desktop'

    # iPhone/iPad UAs contain the literal substring "like Mac OS X" (a
    # long-standing WebKit compatibility quirk), so iOS must be checked
    # before the macOS/Macintosh check or every iPhone reads as a Mac.
    if 'iphone' in ua_l or 'ipad' in ua_l or 'ipod' in ua_l:
        os_name = 'iOS'
    elif 'windows' in ua_l:
        os_name = 'Windows'
    elif 'mac os x' in ua_l or 'macintosh' in ua_l:
        os_name = 'macOS'
    elif 'android' in ua_l:
        os_name = 'Android'
    elif 'linux' in ua_l:
        os_name = 'Linux'
    else:
        os_name = 'Other'

    # Order matters - Edge/Opera/Chrome UAs all also contain "Safari", and
    # Chrome/Edge UAs both contain "Chrome", so check the most specific
    # tokens first.
    if 'edg/' in ua_l or 'edga/' in ua_l or 'edgios/' in ua_l:
        browser = 'Edge'
    elif 'opr/' in ua_l or 'opera' in ua_l:
        browser = 'Opera'
    elif 'firefox' in ua_l or 'fxios' in ua_l:
        browser = 'Firefox'
    elif 'chrome' in ua_l or 'crios' in ua_l:
        browser = 'Chrome'
    elif 'safari' in ua_l:
        browser = 'Safari'
    else:
        browser = 'Other'

    return device_type, os_name, browser


def _truncate_ip(ip: str) -> str:
    """Zero the last IPv4 octet - a privacy-preserving prefix (never store
    or send the full visitor IP) that doubles as a cache key for nearby
    visitors sharing an ISP block."""
    parts = ip.split('.')
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0"
    return ip  # IPv6 or unrecognized - used as-is, rare in practice here


def _client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else None


async def resolve_country(db: AsyncSession, ip: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Best-effort country lookup for a click, without hammering the free
    ipapi.co rate limit (shared with signup location detection) on every
    single click:
    1. Truncate the IP to a /24 prefix - also means the full IP is never
       sent to the third-party lookup service.
    2. Reuse a recently-resolved country for the same prefix if one exists,
       so repeat/nearby visitors cost zero extra API calls.
    3. Otherwise call ipapi.co once for that prefix, with a short timeout.
       Any failure just leaves country as None - it never blocks or fails
       the click recording itself.
    Returns (country, ip_prefix).
    """
    if not ip:
        return None, None
    prefix = _truncate_ip(ip)

    cached = (await db.execute(
        select(LandingClick.country)
        .where(LandingClick.ip_prefix == prefix)
        .where(LandingClick.country.isnot(None))
        .order_by(LandingClick.created_at.desc())
        .limit(1)
    )).scalar()
    if cached:
        return cached, prefix

    try:
        async with httpx.AsyncClient(timeout=2.5) as client:
            resp = await client.get(f"https://ipapi.co/{prefix}/json/")
            if resp.status_code == 200:
                data = resp.json()
                if not data.get('error'):
                    return data.get('country_name'), prefix
    except Exception:
        pass
    return None, prefix


class LandingClickIn(BaseModel):
    link: str
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


@router.post("/landing-click", status_code=204)
async def record_landing_click(
    payload: LandingClickIn,
    request: Request,
    db: AsyncSession = Depends(get_session)
):
    """Record a single click on a landing-page CTA. Fire-and-forget, no auth."""
    device_type, os_name, browser = parse_user_agent(request.headers.get('user-agent'))
    country, ip_prefix = await resolve_country(db, _client_ip(request))

    click = LandingClick(
        link=payload.link[:100],
        referrer=payload.referrer[:500] if payload.referrer else None,
        utm_source=payload.utm_source[:100] if payload.utm_source else None,
        utm_medium=payload.utm_medium[:100] if payload.utm_medium else None,
        utm_campaign=payload.utm_campaign[:100] if payload.utm_campaign else None,
        device_type=device_type,
        os=os_name,
        browser=browser,
        country=country,
        ip_prefix=ip_prefix,
    )
    db.add(click)
    await db.commit()
    return None


class LinkBreakdown(BaseModel):
    link: str
    count: int


class DayBreakdown(BaseModel):
    date: str
    count: int


class CategoryBreakdown(BaseModel):
    label: str
    count: int


class LandingClickStats(BaseModel):
    total: int
    last_24h: int
    by_link_24h: List[LinkBreakdown]
    by_day: List[DayBreakdown]
    by_device: List[CategoryBreakdown]
    by_os: List[CategoryBreakdown]
    by_browser: List[CategoryBreakdown]
    by_country: List[CategoryBreakdown]


@router.get("/landing-clicks", response_model=LandingClickStats)
async def get_landing_click_stats(
    db: AsyncSession = Depends(get_session),
    admin_user: User = Depends(require_admin)
):
    """Admin-only: click counts and breakdowns for the landing page CTAs."""
    since_24h = datetime.utcnow() - timedelta(hours=24)
    since_30d = datetime.utcnow() - timedelta(days=30)

    total = (await db.execute(select(func.count(LandingClick.id)))).scalar() or 0

    last_24h = (await db.execute(
        select(func.count(LandingClick.id)).where(LandingClick.created_at >= since_24h)
    )).scalar() or 0

    link_rows = await db.execute(
        select(LandingClick.link, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_24h)
        .group_by(LandingClick.link)
        .order_by(func.count(LandingClick.id).desc())
    )

    day_rows = await db.execute(
        select(func.date(LandingClick.created_at), func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_30d)
        .group_by(func.date(LandingClick.created_at))
        .order_by(func.date(LandingClick.created_at))
    )

    device_rows = await db.execute(
        select(LandingClick.device_type, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_30d)
        .where(LandingClick.device_type.isnot(None))
        .group_by(LandingClick.device_type)
        .order_by(func.count(LandingClick.id).desc())
    )

    os_rows = await db.execute(
        select(LandingClick.os, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_30d)
        .where(LandingClick.os.isnot(None))
        .group_by(LandingClick.os)
        .order_by(func.count(LandingClick.id).desc())
    )

    browser_rows = await db.execute(
        select(LandingClick.browser, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_30d)
        .where(LandingClick.browser.isnot(None))
        .group_by(LandingClick.browser)
        .order_by(func.count(LandingClick.id).desc())
    )

    country_rows = await db.execute(
        select(LandingClick.country, func.count(LandingClick.id))
        .where(LandingClick.created_at >= since_30d)
        .where(LandingClick.country.isnot(None))
        .group_by(LandingClick.country)
        .order_by(func.count(LandingClick.id).desc())
    )

    return LandingClickStats(
        total=total,
        last_24h=last_24h,
        by_link_24h=[LinkBreakdown(link=link, count=count) for link, count in link_rows.all()],
        by_day=[DayBreakdown(date=str(d), count=c) for d, c in day_rows.all()],
        by_device=[CategoryBreakdown(label=l, count=c) for l, c in device_rows.all()],
        by_os=[CategoryBreakdown(label=l, count=c) for l, c in os_rows.all()],
        by_browser=[CategoryBreakdown(label=l, count=c) for l, c in browser_rows.all()],
        by_country=[CategoryBreakdown(label=l, count=c) for l, c in country_rows.all()],
    )
