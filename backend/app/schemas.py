from pydantic import BaseModel, EmailStr, ConfigDict, Field, computed_field
from typing import Optional, Any, List, Literal
from datetime import datetime, date, time


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    referral_code: Optional[str] = None
    dob: Optional[date] = None
    current_location: Optional[str] = None
    country_code: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    primary_goal: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
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
    country_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def effective_tier(self) -> str:
        """The plan in force right now - `tier` keeps its label after expiry."""
        tier = self.tier or 'free'
        if tier != 'free' and self.tier_expires_at and self.tier_expires_at < datetime.utcnow():
            return 'free'
        return tier


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
    expense_category: Optional[Literal[
        'food', 'transport', 'shopping', 'entertainment', 'bills',
        'health', 'business', 'education', 'marketing', 'other',
    ]] = None
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
    payment_id: int
    provider: Optional[str] = "stripe"
    provider_customer_id: Optional[str] = None
    plan: Optional[str] = None
    duration_days: Optional[int] = None
    discount_pct: Optional[float] = None
    amount_paid: Optional[float] = None
    currency: Optional[str] = None
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
    days_remaining: Optional[int] = None
    auto_renew: Optional[bool] = None
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
    succeeded_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ── Referral commissions / withdrawals / refunds ──
class WalletBalance(BaseModel):
    currency: str
    pending: float
    available: float
    paid: float


class ReferralWalletOut(BaseModel):
    balances: List[WalletBalance]
    min_withdrawal_usd_equivalent: float


class ReferralStatsOut(BaseModel):
    referral_count: int
    lifetime_earned: float
    rank: Optional[int] = None
    total_ranked: Optional[int] = None


class CommissionOut(BaseModel):
    id: int
    created_at: datetime
    referred_username: str
    sequence_number: int
    commission_rate: float
    commission_amount: float
    currency: str
    status: str  # pending/available/paid/voided
    available_at: datetime


class WithdrawalRequestCreate(BaseModel):
    currency: str
    payout_destination: Optional[str] = None


class WithdrawalRequestOut(BaseModel):
    id: int
    user_id: int
    amount: float
    currency: str
    status: str
    payout_destination: Optional[str] = None
    requested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class RefundRequestCreate(BaseModel):
    reason: Optional[str] = None


class RefundRequestOut(BaseModel):
    id: int
    user_id: int
    payment_id: int
    reason: Optional[str] = None
    status: str
    requested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    admin_notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AdminActionNote(BaseModel):
    admin_notes: Optional[str] = None


class StripePaymentRequest(BaseModel):
    customer_id: Optional[str] = None
    price_id: str
    tier: Optional[str] = 'tier1'


class MpesaPaymentRequest(BaseModel):
    phone_number: str
    amount: float = Field(..., gt=0)
    tier: Optional[str] = 'tier1'


class PaystackPaymentRequest(BaseModel):
    email: str
    amount: float = Field(..., gt=0)
    currency: Optional[str] = 'KES'
    callback_url: Optional[str] = None
    tier: Optional[str] = 'tier1'
    special_offer: Optional[bool] = False


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


# ─────────────────────────────────────────────
#  CASHPOOL  (savings & spending discipline)
# ─────────────────────────────────────────────
# Amounts are in the user's own currency. Rates are fractions (0.35 = 35%).
class CashpoolUpdate(BaseModel):
    target_savings_rate: Optional[float] = Field(None, ge=0, le=1)
    target_monthly_savings: Optional[float] = Field(None, ge=0)
    daily_spend_cap: Optional[float] = Field(None, ge=0)
    weekly_spend_cap: Optional[float] = Field(None, ge=0)
    monthly_spend_cap: Optional[float] = Field(None, ge=0)
    target_runway_days: Optional[float] = Field(None, ge=0)
    emergency_fund_target: Optional[float] = Field(None, ge=0)
    alert_on_cap_breach: Optional[bool] = None
    alert_on_low_runway: Optional[bool] = None
    alert_on_savings_miss: Optional[bool] = None


class CashpoolOut(BaseModel):
    target_savings_rate: Optional[float] = None
    current_savings_rate: Optional[float] = None
    total_savings: Optional[float] = None
    target_monthly_savings: Optional[float] = None
    daily_spend_cap: Optional[float] = None
    weekly_spend_cap: Optional[float] = None
    monthly_spend_cap: Optional[float] = None
    cap_breach_count: int = 0
    last_cap_breach_at: Optional[datetime] = None
    current_runway_days: Optional[float] = None
    target_runway_days: Optional[float] = None
    emergency_fund_target: Optional[float] = None
    emergency_fund_current: Optional[float] = None
    emergency_fund_met: bool = False
    period_start: Optional[date] = None
    period_income: Optional[float] = None
    period_expenses: Optional[float] = None
    period_savings: Optional[float] = None
    period_days_logged: Optional[int] = None
    alert_on_cap_breach: bool = True
    alert_on_low_runway: bool = True
    alert_on_savings_miss: bool = True
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# ─────────────────────────────────────────────
#  XP  (points are awarded server-side only, for new daily logs)
# ─────────────────────────────────────────────
class UserPointsOut(BaseModel):
    total_points: int = 0
    level: int = 1
    xp_into_level: int = 0
    xp_level_span: int = 100
    points_to_next: int = 100
    model_config = ConfigDict(from_attributes=True)
