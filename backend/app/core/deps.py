from datetime import datetime
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.security import decode_access_token
from app import crud

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_effective_tier(user) -> str:
    """The tier a user is actually entitled to right now.

    User.tier is a cached label set at purchase time and never reverted -
    tier_expires_at is written correctly on every purchase but was never
    read anywhere, so a lapsed paid subscription kept full paid access
    forever. Callers that gate a feature on tier must use this, not
    user.tier directly.
    """
    tier = user.tier or 'free'
    if tier != 'free' and user.tier_expires_at and user.tier_expires_at < datetime.utcnow():
        return 'free'
    return tier


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    sub = payload.get("sub")
    try:
        user_id = int(sub)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
