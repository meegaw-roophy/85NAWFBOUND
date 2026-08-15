from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from datetime import datetime
import os
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


@router.patch("/users/{user_id}/reports/{report_id}/share")
async def update_report_sharing(
    user_id: int,
    report_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user)
):
    """Update report sharing settings"""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    
    report = await crud.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    
    # Update sharing settings
    if 'share_with_public' in payload:
        report.share_with_public = payload['share_with_public']
    if 'share_with_circles' in payload:
        report.share_with_circles = payload['share_with_circles']
    if 'share_anonymously' in payload:
        report.share_anonymously = payload['share_anonymously']
    if 'custom_message' in payload:
        report.custom_message = payload['custom_message']
    if 'share_theme' in payload:
        report.share_theme = payload['share_theme']
    if 'share_password' in payload:
        report.share_password = payload['share_password']
    if 'share_expires_at' in payload:
        report.share_expires_at = payload['share_expires_at']
    
    # Generate shareable link if enabling public sharing and no link exists
    if payload.get('share_with_public') and not report.link_url:
        import secrets
        share_token = secrets.token_urlsafe(16)
        report.link_url = f"{os.getenv('APP_URL', 'https://vektra-backend-qic7.onrender.com')}/shared/{share_token}"
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    return {
        "id": report.id,
        "link_url": report.link_url,
        "share_with_public": report.share_with_public,
        "share_with_circles": report.share_with_circles,
        "share_anonymously": report.share_anonymously,
        "custom_message": report.custom_message,
        "share_theme": report.share_theme,
        "share_expires_at": report.share_expires_at
    }


@router.get("/shared/{share_token}")
async def get_shared_report(share_token: str, db: AsyncSession = Depends(get_session)):
    """Get a publicly shared report by token"""
    from app.db.models import Report
    from sqlalchemy import select
    
    result = await db.execute(
        select(Report).where(Report.link_url.like(f"%{share_token}"))
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not report.share_with_public:
        raise HTTPException(status_code=403, detail="Report is not publicly shared")
    
    # Check if sharing has expired
    if report.share_expires_at and report.share_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share link has expired")
    
    # Return anonymous version if requested
    response_data = {
        "content": report.content,
        "summary_text": report.summary_text,
        "vektra_score": report.vektra_score,
        "report_type": report.report_type,
        "generated_at": report.generated_at,
        "custom_message": report.custom_message,
        "share_theme": report.share_theme
    }
    
    if not report.share_anonymously:
        # Include user info if not anonymous
        user_result = await db.execute(select(User).where(User.id == report.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            response_data["user"] = {
                "username": user.username,
                "full_name": user.full_name
            }
    
    return response_data
