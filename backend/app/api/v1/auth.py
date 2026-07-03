from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import UserCreate, UserOut, Token
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
    user = await crud.create_user(db, username=payload.username, email=payload.email, password_hash=pw_hash, full_name=payload.full_name, dob=payload.dob, current_location=payload.current_location, language=payload.language, primary_goal=payload.primary_goal)
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
