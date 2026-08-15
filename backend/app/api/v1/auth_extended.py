from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_session
from app.db.models import User
from app.core.security import create_access_token
from app.core.deps import get_current_user
from datetime import datetime, timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

router = APIRouter()


def generate_verification_token():
    """Generate a secure random token for email verification"""
    return secrets.token_urlsafe(32)


def generate_reset_token():
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)


async def send_verification_email(email: str, token: str):
    """Send verification email with token"""
    # TODO: Integrate with email service (SendGrid, Mailgun, etc.)
    # For now, return success (will need actual email service integration)
    print(f"VERIFICATION EMAIL: To: {email}, Token: {token}")
    # In production, use actual email service
    return True


async def send_password_reset_email(email: str, token: str):
    """Send password reset email with token"""
    # TODO: Integrate with email service
    print(f"PASSWORD RESET EMAIL: To: {email}, Token: {token}")
    return True


@router.post("/auth/resend-verification")
async def resend_verification_email(
    email: str,
    db: AsyncSession = Depends(get_session)
):
    """Resend verification email to user"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Generate new token
    token = generate_verification_token()
    user.verification_token = token
    user.verification_expires_at = datetime.utcnow() + timedelta(hours=24)
    
    db.add(user)
    await db.commit()
    
    # Send email
    await send_verification_email(user.email, token)
    
    return {"message": "Verification email sent"}


@router.post("/auth/verify-email")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_session)
):
    """Verify email using token"""
    result = await db.execute(
        select(User).where(
            User.verification_token == token,
            User.verification_expires_at > datetime.utcnow()
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user.is_verified = True
    user.verification_token = None
    user.verification_expires_at = None
    
    db.add(user)
    await db.commit()
    
    return {"message": "Email verified successfully"}


@router.post("/auth/request-password-reset")
async def request_password_reset(
    email: str,
    db: AsyncSession = Depends(get_session)
):
    """Request password reset email"""
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if user exists for security
        return {"message": "If email exists, reset link sent"}
    
    # Generate reset token
    token = generate_reset_token()
    user.reset_token = token
    user.reset_expires_at = datetime.utcnow() + timedelta(hours=1)
    
    db.add(user)
    await db.commit()
    
    # Send email
    await send_password_reset_email(user.email, token)
    
    return {"message": "If email exists, reset link sent"}


@router.post("/auth/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: AsyncSession = Depends(get_session)
):
    """Reset password using token"""
    result = await db.execute(
        select(User).where(
            User.reset_token == token,
            User.reset_expires_at > datetime.utcnow()
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # Validate password
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Update password
    from app.core.security import get_password_hash
    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_expires_at = None
    
    db.add(user)
    await db.commit()
    
    return {"message": "Password reset successfully"}


@router.get("/auth/verification-status")
async def get_verification_status(
    current_user: User = Depends(get_current_user)
):
    """Check if current user's email is verified"""
    return {
        "is_verified": current_user.is_verified,
        "email": current_user.email
    }
