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

