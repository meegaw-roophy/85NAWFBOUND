from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User, Snapshot
from .snapshots import router as snapshots_router
from .reports import router as reports_router
from .auth import router as auth_router
from .payments import router as payments_router
from .webhooks import router as webhooks_router
from .users import router as users_router
from .goals import router as goals_router
from .admin import router as admin_router
from .subscriptions import router as subscriptions_router
from .achievements import router as achievements_router
from .export import router as export_router
from .circles import router as circles_router
from .streak import router as streak_router
from .flex import router as flex_router
from .insights import router as insights_router
from .wagers import router as wagers_router
from .trash_talk import router as trash_talk_router
from .notifications import router as notifications_router

router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok"}


router.include_router(admin_router, prefix="/admin", tags=["admin"])
router.include_router(snapshots_router)
router.include_router(reports_router)
router.include_router(payments_router)
router.include_router(webhooks_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(goals_router, prefix="/goals", tags=["goals"])
router.include_router(subscriptions_router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(achievements_router, prefix="/achievements", tags=["achievements"])
router.include_router(export_router, prefix="/export", tags=["export"])
router.include_router(circles_router, prefix="/circles", tags=["circles"])
router.include_router(streak_router, prefix="/streak", tags=["streak"])
router.include_router(flex_router, prefix="/flex", tags=["flex"])
router.include_router(insights_router, prefix="/insights", tags=["insights"])
router.include_router(wagers_router, prefix="/wagers", tags=["wagers"])
router.include_router(trash_talk_router, prefix="/trash-talk", tags=["trash-talk"])
router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

