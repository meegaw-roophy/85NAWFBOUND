from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional, Any, List
from datetime import datetime
from enum import Enum


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        return v


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


# --- Goals ---

class GoalCategoryEnum(str, Enum):
    financial = "financial"
    wellness = "wellness"
    career = "career"
    education = "education"
    fitness = "fitness"
    custom = "custom"


class GoalStatusEnum(str, Enum):
    active = "active"
    completed = "completed"
    paused = "paused"
    cancelled = "cancelled"


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: GoalCategoryEnum = GoalCategoryEnum.custom
    target_value: Optional[float] = None
    current_value: float = 0.0
    unit: Optional[str] = None
    deadline: Optional[datetime] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[GoalCategoryEnum] = None
    status: Optional[GoalStatusEnum] = None
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    unit: Optional[str] = None
    deadline: Optional[datetime] = None


class GoalOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    category: GoalCategoryEnum
    status: GoalStatusEnum
    target_value: Optional[float]
    current_value: float
    unit: Optional[str]
    deadline: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

    @property
    def progress_percent(self) -> Optional[float]:
        if self.target_value and self.target_value > 0:
            return round((self.current_value / self.target_value) * 100, 1)
        return None
