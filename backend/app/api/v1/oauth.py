from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User
from app.core.security import create_access_token
from app.core.deps import get_current_user
from datetime import datetime, timedelta
import secrets

router = APIRouter()


@router.post("/auth/oauth/google")
async def google_oauth_login(
    payload: dict,
    db: AsyncSession = Depends(get_session)
):
    """Handle Google OAuth login/callback"""
    # TODO: Verify Google ID token with Google's API
    # For now, we'll implement a placeholder that accepts the token
    
    google_id = payload.get('google_id')
    email = payload.get('email')
    name = payload.get('name')
    access_token = payload.get('access_token')
    
    if not google_id or not email:
        raise HTTPException(status_code=400, detail="google_id and email are required")
    
    # Check if user exists with this Google ID
    result = await db.execute(
        select(User).where(
            User.oauth_provider == 'google',
            User.oauth_id == google_id
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update access token
        user.oauth_access_token = access_token
        user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Generate JWT token
        token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "tier": user.tier
            }
        }
    else:
        # Check if user exists with this email
        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # Link existing account with Google
            existing_user.oauth_provider = 'google'
            existing_user.oauth_id = google_id
            existing_user.oauth_access_token = access_token
            existing_user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
            db.add(existing_user)
            await db.commit()
            await db.refresh(existing_user)
            
            token = create_access_token(data={"sub": str(existing_user.id)})
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": existing_user.id,
                    "username": existing_user.username,
                    "email": existing_user.email,
                    "tier": existing_user.tier
                }
            }
        else:
            # Create new user
            username = email.split('@')[0]
            # Ensure username is unique
            result = await db.execute(select(User).where(User.username == username))
            if result.scalar_one_or_none():
                username = f"{username}_{secrets.token_hex(4)}"
            
            new_user = User(
                username=username,
                email=email,
                full_name=name,
                oauth_provider='google',
                oauth_id=google_id,
                oauth_access_token=access_token,
                oauth_token_expires_at=datetime.utcnow() + timedelta(hours=1),
                is_verified=True,  # OAuth users are pre-verified
                tier='free'
            )
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            
            token = create_access_token(data={"sub": str(new_user.id)})
            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "tier": new_user.tier
                }
            }


@router.post("/auth/oauth/apple")
async def apple_oauth_login(
    payload: dict,
    db: AsyncSession = Depends(get_session)
):
    """Handle Apple OAuth login/callback"""
    # TODO: Verify Apple ID token with Apple's API
    
    apple_id = payload.get('apple_id')
    email = payload.get('email')
    name = payload.get('name')
    access_token = payload.get('access_token')
    
    if not apple_id:
        raise HTTPException(status_code=400, detail="apple_id is required")
    
    # Check if user exists with this Apple ID
    result = await db.execute(
        select(User).where(
            User.oauth_provider == 'apple',
            User.oauth_id == apple_id
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.oauth_access_token = access_token
        user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "tier": user.tier
            }
        }
    else:
        # Apple may not provide email on subsequent logins
        if email:
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                existing_user.oauth_provider = 'apple'
                existing_user.oauth_id = apple_id
                existing_user.oauth_access_token = access_token
                existing_user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
                db.add(existing_user)
                await db.commit()
                await db.refresh(existing_user)
                
                token = create_access_token(data={"sub": str(existing_user.id)})
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "id": existing_user.id,
                        "username": existing_user.username,
                        "email": existing_user.email,
                        "tier": existing_user.tier
                    }
                }
        
        # Create new user
        username = f"apple_user_{secrets.token_hex(4)}"
        new_user = User(
            username=username,
            email=email,
            full_name=name,
            oauth_provider='apple',
            oauth_id=apple_id,
            oauth_access_token=access_token,
            oauth_token_expires_at=datetime.utcnow() + timedelta(hours=1),
            is_verified=True,
            tier='free'
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        token = create_access_token(data={"sub": str(new_user.id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "tier": new_user.tier
            }
        }


@router.post("/auth/oauth/github")
async def github_oauth_login(
    payload: dict,
    db: AsyncSession = Depends(get_session)
):
    """Handle GitHub OAuth login/callback"""
    # TODO: Verify GitHub token with GitHub's API
    
    github_id = payload.get('github_id')
    email = payload.get('email')
    login = payload.get('login')
    access_token = payload.get('access_token')
    
    if not github_id or not login:
        raise HTTPException(status_code=400, detail="github_id and login are required")
    
    # Check if user exists with this GitHub ID
    result = await db.execute(
        select(User).where(
            User.oauth_provider == 'github',
            User.oauth_id == str(github_id)
        )
    )
    user = result.scalar_one_or_none()
    
    if user:
        user.oauth_access_token = access_token
        user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "tier": user.tier
            }
        }
    else:
        if email:
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                existing_user.oauth_provider = 'github'
                existing_user.oauth_id = str(github_id)
                existing_user.oauth_access_token = access_token
                existing_user.oauth_token_expires_at = datetime.utcnow() + timedelta(hours=1)
                db.add(existing_user)
                await db.commit()
                await db.refresh(existing_user)
                
                token = create_access_token(data={"sub": str(existing_user.id)})
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "id": existing_user.id,
                        "username": existing_user.username,
                        "email": existing_user.email,
                        "tier": existing_user.tier
                    }
                }
        
        # Create new user
        username = login
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            username = f"{login}_{secrets.token_hex(4)}"
        
        new_user = User(
            username=username,
            email=email,
            full_name=login,
            oauth_provider='github',
            oauth_id=str(github_id),
            oauth_access_token=access_token,
            oauth_token_expires_at=datetime.utcnow() + timedelta(hours=1),
            is_verified=True,
            tier='free'
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        token = create_access_token(data={"sub": str(new_user.id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "tier": new_user.tier
            }
        }


@router.post("/auth/oauth/unlink")
async def unlink_oauth(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Unlink OAuth provider from user account"""
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
async def get_linked_providers(
    current_user: User = Depends(get_current_user)
):
    """Get list of OAuth providers linked to user account"""
    providers = []
    if current_user.oauth_provider:
        providers.append({
            "provider": current_user.oauth_provider,
            "linked_date": current_user.created_at.isoformat() if current_user.created_at else None
        })
    return {"providers": providers}
