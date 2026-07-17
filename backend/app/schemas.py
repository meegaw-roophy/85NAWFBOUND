from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Any
from datetime import datetime, date, time


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    dob: Optional[date] = None
    current_location: Optional[str] = None
    language: Optional[str] = None
    primary_goal: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    primary_goal: Optional[str] = None
    north_star: Optional[str] = None
    north_star_deadline: Optional[date] = None
    initial_net_worth: Optional[float] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    preferred_feedback_tone: Optional[str] = None
    ai_tone_language: Optional[str] = None
    tier: Optional[str] = None
    tier_expires_at: Optional[datetime] = None  # 2. RECOMMENDED: Kept as datetime/date or string
    created_at: Optional[datetime] = None
    current_location: Optional[str] = None


# ─────────────────────────────────────────────
#  SNAPSHOT  (daily log — matches full VEKTRA model)
# ─────────────────────────────────────────────
class SnapshotCreate(BaseModel):
    timestamp: Optional[datetime] = None
    log_date: Optional[date] = None

    # mental & emotional
    mood_score: Optional[int] = None
    energy_level: Optional[int] = None
    focus_level: Optional[int] = None
    social_battery: Optional[int] = None
    health_battery: Optional[int] = None
    uncomfortable_moments: Optional[str] = None
    future_self_message: Optional[str] = None
    ai_accuracy: Optional[int] = None

    # body & health
    sleep_hours: Optional[float] = None
    body_weight: Optional[float] = None
    diet_taken: Optional[str] = None
    screen_time: Optional[float] = None

    # finance
    daily_income: Optional[float] = None
    expenses: Optional[float] = None
    savings_investments: Optional[float] = None
    current_net_worth: Optional[float] = None
    current_capital: Optional[float] = None
    any_emergency: Optional[str] = None
    emergency_amount: Optional[float] = None

    # goals & decisions
    tomorrow_goal: Optional[str] = None
    target_hit_and_why: Optional[str] = None
    target_hit_bool: Optional[bool] = None
    best_decision: Optional[str] = None
    worst_decision: Optional[str] = None
    lessons_learned: Optional[str] = None
    what_i_avoided: Optional[str] = None
    risk_taken: Optional[str] = None

    # learning & growth
    skills_learned: Optional[str] = None
    new_ideas: Optional[str] = None
    interactions_done: Optional[str] = None
    interaction_outcome: Optional[str] = None
    gratitude_line: Optional[str] = None
    funny_line: Optional[str] = None
    quotes_insights: Optional[str] = None

    # performance & focus
    focus_hours: Optional[float] = None
    environment_rating: Optional[int] = None
    opportunity_cost: Optional[float] = None
    last_trash_talk_sent: Optional[datetime] = None
    trash_talk_count: Optional[int] = None

    # weekly inputs
    how_many_goals: Optional[int] = None
    decision_speed: Optional[float] = None
    goal_intensity: Optional[Any] = None

    # overflow
    data: Optional[Any] = None


class SnapshotStatusOut(BaseModel):
    logged: bool


class SnapshotOut(SnapshotCreate):
    id: int
    user_id: int

    # computed fields (returned, never set by user)
    net_worth_variance: Optional[float] = None
    burn_rate: Optional[float] = None
    resilience_score: Optional[float] = None
    survival_runway: Optional[float] = None
    procrastination_delta: Optional[float] = None
    leverage_score: Optional[float] = None
    system_leak: Optional[float] = None
    mistake_correlation: Optional[float] = None
    goal_completion_pct: Optional[float] = None
    opportunity_cost_score: Optional[float] = None
    vektra_score: Optional[float] = None
    is_duplicate: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class ReportCreate(BaseModel):
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    report_type: Optional[str] = "weekly"


class ReportOut(BaseModel):
    id: int
    user_id: int
    generated_at: Optional[datetime]
    report_type: Optional[str] = None
    status: Optional[str] = None
    content: Optional[Any]
    summary_text: Optional[str]
    vektra_score: Optional[float] = None
    link_url: Optional[str] = None
    image_urls: Optional[Any] = None
    pdf_url: Optional[str] = None
    video_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(BaseModel):
    provider: Optional[str] = "stripe"
    provider_customer_id: Optional[str] = None
    plan: Optional[str] = None
    duration_days: Optional[int] = None
    active: bool = True


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    provider: str
    provider_customer_id: Optional[str]
    plan: Optional[str]
    duration_days: Optional[int] = None
    discount_pct: Optional[float] = None
    days_free: Optional[int] = None
    amount_paid: Optional[float] = None
    currency: Optional[str] = None
    active: bool
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class PaymentCreate(BaseModel):
    provider: str
    provider_customer_id: Optional[str] = None
    provider_payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = 'usd'
    status: Optional[str] = 'pending'
    external_response: Optional[Any] = None


class PaymentUpdate(BaseModel):
    status: str
    external_response: Optional[Any] = None


class PaymentOut(BaseModel):
    id: int
    user_id: int
    provider: str
    provider_customer_id: Optional[str]
    provider_payment_id: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    status: str
    external_response: Optional[Any]
    created_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class StripePaymentRequest(BaseModel):
    customer_id: Optional[str] = None
    price_id: str


class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoalCreate(BaseModel):
    title: str
    is_primary: Optional[bool] = False
    intensity: Optional[int] = None
    effort: Optional[int] = None
    deadline: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    is_primary: Optional[bool] = None
    intensity: Optional[int] = None
    effort: Optional[int] = None
    deadline: Optional[date] = None
    completed: Optional[bool] = None
    progress_pct: Optional[float] = None


class GoalOut(BaseModel):
    id: int
    user_id: int
    title: str
    is_primary: bool
    intensity: Optional[int] = None
    effort: Optional[int] = None
    deadline: Optional[date] = None
    completed: bool
    completion_date: Optional[datetime] = None
    progress_pct: float
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AchievementCreate(BaseModel):
    achievement_id: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    rarity: Optional[str] = "common"


class AchievementOut(BaseModel):
    id: int
    user_id: int
    achievement_id: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = None
    rarity: Optional[str] = None
    progress: float
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)