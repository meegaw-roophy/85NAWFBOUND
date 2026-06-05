from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserCreate, UserOut, Token, UserUpdate, PasswordChange
from app.db.session import get_session
from app import crud
from app.db.models import User
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.deps import get_current_user

router = APIRouter()


@router.post("/auth/register", response_model=UserOut)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_session)):
    # Check for existing username/email
    existing = await crud.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    existing_e = await crud.get_user_by_email(db, payload.email)
    if existing_e:
        raise HTTPException(status_code=400, detail="Email already registered")
    pw_hash = get_password_hash(payload.password)
    user = await crud.create_user(db, username=payload.username, email=payload.email, password_hash=pw_hash)
    return user


@router.post("/auth/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_session)):
    # find user by username
    user = await crud.get_user_by_username(db, form_data.username)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/users/me", response_model=UserOut)
async def update_profile(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    update_data = payload.model_dump(exclude_unset=True)
    if "username" in update_data:
        existing = await crud.get_user_by_username(db, update_data["username"])
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
    if "email" in update_data:
        existing = await crud.get_user_by_email(db, update_data["email"])
        if existing and existing.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already registered")
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/users/me/password")
async def change_password(
    payload: PasswordChange,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password updated successfully"}
