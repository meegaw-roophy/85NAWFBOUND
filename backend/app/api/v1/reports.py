from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.schemas import ReportCreate, ReportOut
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.core.deps import get_current_user
from app.services.report_service import generate_and_store_report

router = APIRouter()


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
