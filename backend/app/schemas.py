from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SnapshotCreate(BaseModel):
    timestamp: Optional[datetime] = None
    data: Optional[Any] = None
    mood: Optional[int] = None
    energy: Optional[int] = None
    focus: Optional[int] = None
    income: Optional[float] = None
    expenses: Optional[float] = None
    savings: Optional[float] = None


class SnapshotOut(SnapshotCreate):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ReportCreate(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class ReportOut(BaseModel):
    id: int
    user_id: int
    generated_at: Optional[datetime]
    content: Optional[Any]
    summary_text: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(BaseModel):
    provider: Optional[str] = "stripe"
    provider_customer_id: Optional[str]
    plan: Optional[str]
    active: bool = True


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    provider: str
    provider_customer_id: Optional[str]
    plan: Optional[str]
    active: bool
    created_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class StripePaymentRequest(BaseModel):
    customer_id: Optional[str]
    price_id: str


class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
