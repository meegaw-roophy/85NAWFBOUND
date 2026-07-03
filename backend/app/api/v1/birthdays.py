import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.deps import get_current_user
from app.db.models import User
from app.services.birthday_service import birthday_service

router = APIRouter()


@router.get("/birthdays/today")
async def get_birthdays_today(db: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Get list of users whose birthday is today.
    Admin-only endpoint (for now, requires auth).
    """
    birthday_users = await birthday_service.check_birthdays_today(db)
    return {
        "count": len(birthday_users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "dob": u.dob.isoformat() if u.dob else None
            }
            for u in birthday_users
        ]
    }


@router.post("/birthdays/generate")
async def generate_birthday_wishes(db: AsyncSession = Depends(get_session), current_user: User = Depends(get_current_user)):
    """
    Generate birthday images and messages for all users with birthdays today.
    Returns list of generated content.
    """
    results = await birthday_service.send_birthday_wishes(db)
    return {
        "generated": len(results),
        "content": results
    }


@router.get("/birthdays/my-birthday")
async def get_my_birthday_status(current_user: User = Depends(get_current_user)):
    """
    Check if today is the current user's birthday.
    Returns birthday info if today is their birthday.
    """
    if not current_user.dob:
        return {"is_birthday": False, "message": "No date of birth set"}
    
    today = datetime.datetime.utcnow().date()
    is_birthday = (current_user.dob.month == today.month and current_user.dob.day == today.day)
    
    if is_birthday:
        age = today.year - current_user.dob.year - ((today.month, today.day) < (current_user.dob.month, current_user.dob.day))
        return {
            "is_birthday": True,
            "age": age,
            "message": f"Happy {age}th Birthday! 🎉"
        }
    
    return {"is_birthday": False, "message": "Today is not your birthday"}
