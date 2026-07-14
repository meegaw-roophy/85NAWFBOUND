"""
Data Export API
Handles exporting user data in various formats (CSV, JSON).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.auth import get_current_user
from app.db.models import User
from app import crud

router = APIRouter()


@router.get("/csv")
async def export_csv(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Export user data as CSV"""
    csv_data = await crud.export_user_data_csv(db, current_user.id)
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vektra_export_{current_user.username}.csv"
        }
    )


@router.get("/json")
async def export_json(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Export user data as JSON"""
    json_data = await crud.export_user_data_json(db, current_user.id)
    
    import json
    json_str = json.dumps(json_data, indent=2)
    
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=vektra_export_{current_user.username}.json"
        }
    )
