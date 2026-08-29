from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User
from app.core.security import create_access_token, get_password_hash
from app.core.deps import get_current_user
from app.core.config import settings
import secrets

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

router = APIRouter()


@router.post("/auth/oauth/google")
async def google_oauth_login(
    payload: dict,
    db: AsyncSession = Depends(get_session)
):
    """Handle Google Sign-In.

    The client sends the ID token (credential) issued by Google Identity
    Services - never a raw email/id pair. This verifies that token's
    signature and audience directly with Google before trusting any of the
    identity fields inside it. A previous version of this endpoint accepted
    client-supplied email/google_id with no verification at all, which let
    anyone log in as anyone; that version is gone.
    """
    credential = payload.get("credential") or payload.get("id_token")
    if not credential:
        raise HTTPException(status_code=400, detail="credential is required")

    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=501, detail="Google sign-in is not configured")

    try:
        idinfo = google_id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    google_id = idinfo.get("sub")
    email = idinfo.get("email")
    name = idinfo.get("name")
    email_verified = idinfo.get("email_verified", False)

    if not google_id or not email or not email_verified:
        raise HTTPException(status_code=400, detail="Google account has no verified email")

    result = await db.execute(
        select(User).where(User.oauth_provider == "google", User.oauth_id == google_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Existing password-based account with a matching, Google-verified
            # email - link it rather than creating a duplicate.
            user.oauth_provider = "google"
            user.oauth_id = google_id
            db.add(user)
        else:
            username = email.split("@")[0]
            existing_username = await db.execute(select(User).where(User.username == username))
            if existing_username.scalar_one_or_none():
                username = f"{username}_{secrets.token_hex(4)}"

            user = User(
                username=username,
                email=email,
                # Unusable random password - this account only ever signs in
                # via Google, but password_hash is a required column.
                password_hash=get_password_hash(secrets.token_urlsafe(32)),
                full_name=name,
                oauth_provider="google",
                oauth_id=google_id,
                is_verified=True,
                tier="free",
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

    token = create_access_token(subject=str(user.id))
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "tier": user.tier,
        },
    }


@router.post("/auth/oauth/unlink")
async def unlink_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Unlink an OAuth provider from the authenticated user's own account."""
    if current_user.oauth_provider != provider:
        raise HTTPException(status_code=400, detail="User is not linked to this provider")

    current_user.oauth_provider = None
    current_user.oauth_id = None
    current_user.oauth_access_token = None
    current_user.oauth_refresh_token = None
    current_user.oauth_token_expires_at = None

    db.add(current_user)
    await db.commit()

    return {"message": f"Successfully unlinked {provider}"}


@router.get("/auth/oauth/providers")
async def get_linked_providers(current_user: User = Depends(get_current_user)):
    """List OAuth providers linked to the authenticated user's own account."""
    providers = []
    if current_user.oauth_provider:
        providers.append({
            "provider": current_user.oauth_provider,
            "linked_date": current_user.created_at.isoformat() if current_user.created_at else None,
        })
    return {"providers": providers}
