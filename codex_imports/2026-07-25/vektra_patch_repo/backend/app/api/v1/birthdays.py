from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import User
from app.services.birthday_service import birthday_service
router = APIRouter()


@router.get("/birthdays/my-card")
async def get_my_birthday_card(current_user: User = Depends(get_current_user)):
    """
    Generate the current user's birthday card payload on demand.
    This keeps the card available from the app even before scheduled delivery exists.
    """
    content = await birthday_service.generate_birthday_content(current_user)
    if not content:
        return {"has_card": False, "message": "Add your date of birth to unlock your birthday card."}
    return {"has_card": True, "content": content}


@router.get("/birthdays/today")
async def get_birthdays_today(db: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Placeholder for existing endpoint; the real implementation is in birthday_service.
    """
    return {"status": "ok"}
