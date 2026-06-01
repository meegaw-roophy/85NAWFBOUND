from fastapi import APIRouter
from .snapshots import router as snapshots_router
from .reports import router as reports_router
from .auth import router as auth_router
from .payments import router as payments_router

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


router.include_router(snapshots_router)
router.include_router(reports_router)
router.include_router(payments_router)
router.include_router(auth_router)
