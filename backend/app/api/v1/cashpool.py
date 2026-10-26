from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core.deps import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.schemas import CashpoolOut, CashpoolUpdate

router = APIRouter()


@router.get("", response_model=CashpoolOut)
async def get_cashpool(db: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """Settings plus last-30-days metrics, recomputed from the user's logs on every read."""
    return await crud.recalculate_cashpool_metrics(db, current_user.id)


@router.put("", response_model=CashpoolOut)
async def update_cashpool(
    payload: CashpoolUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    cashpool = await crud.get_or_create_cashpool(db, current_user.id)
    return await crud.update_cashpool(db, cashpool, payload.model_dump(exclude_unset=True))


@router.get("/spending-by-category")
async def spending_by_category(
    days: int = Query(crud.CASHPOOL_WINDOW_DAYS, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return {"period_days": days, "categories": await crud.get_spending_by_category(db, current_user.id, days)}
