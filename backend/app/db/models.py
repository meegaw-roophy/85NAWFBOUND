from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime,
    JSON, Float, Boolean, Text, Date, Time
)
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()


# ─────────────────────────────────────────────
#  USER
# ─────────────────────────────────────────────
class User(Base):
    __tablename__ = 'users'

    id                      = Column(Integer, primary_key=True, index=True)
    created_at              = Column(DateTime, default=datetime.datetime.utcnow)

    # ── identity ──────────────────────────────
    username                = Column(String(50),  unique=True, index=True, nullable=False)
    email                   = Column(String(255), unique=True, index=True, nullable=False)
    password_hash           = Column(String(255), nullable=False)
    full_name               = Column(String(255), nullable=True)
    dob                     = Column(Date,        nullable=True)   # birthday card trigger + age calc

    # ── financial baseline ────────────────────
    initial_net_worth       = Column(Float,       nullable=True, default=0.0)
    currency                = Column(String(10),  nullable=True, default='USD')  # auto-detected

    # ── preferences ───────────────────────────
    language                = Column(String(50),  nullable=True, default='English')
    preferred_feedback_tone = Column(String(50),  nullable=True, default='Balanced')  # Harsh / Balanced / Gentle
    ai_tone_language        = Column(String(50),  nullable=True, default='Motivational')  # Professional / Casual / Motivational
    reminder_time           = Column(Time,        nullable=True)  # daily push notification time

    # ── north star ────────────────────────────
    primary_goal            = Column(Text,        nullable=True)  # main goal in words
    north_star              = Column(Text,        nullable=True)  # goal + deadline combined
    north_star_deadline     = Column(Date,        nullable=True)  # parsed deadline from north_star

    # ── subscription tier ─────────────────────
    tier                    = Column(String(20),  nullable=True, default='free')  # free / tier1 / tier2 / tier3
    tier_expires_at         = Column(DateTime,    nullable=True)

    # ── location (for PPP pricing) ────────────
    current_location        = Column(String(100), nullable=True)

    # ── relationships ─────────────────────────
    snapshots               = relationship('Snapshot',    back_populates='user', cascade='all, delete')
    reports                 = relationship('Report',      back_populates='user', cascade='all, delete')
    subscriptions           = relationship('Subscription',back_populates='user', cascade='all, delete')
    goals                   = relationship('Goal',        back_populates='user', cascade='all, delete')
    vek_credits             = relationship('VekCredit',   back_populates='user', cascade='all, delete')
    referrals_made          = relationship('Referral',    foreign_keys='Referral.referrer_id', back_populates='referrer', cascade='all, delete')


# ─────────────────────────────────────────────
#  GOAL  (north star broken into subgoals)
# ─────────────────────────────────────────────
class Goal(Base):
    __tablename__ = 'goals'

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)

    title           = Column(Text,    nullable=False)           # the subgoal description
    is_primary      = Column(Boolean, default=False)            # true = north star goal
    intensity       = Column(Integer, nullable=True)            # 1-10 urgency/priority
    effort          = Column(Integer, nullable=True)            # 1-10 effort required
    deadline        = Column(Date,    nullable=True)
    completed       = Column(Boolean, default=False)
    completion_date = Column(DateTime,nullable=True)
    progress_pct    = Column(Float,   default=0.0)              # 0-100 computed weekly

    user            = relationship('User', back_populates='goals')


# ─────────────────────────────────────────────
#  SNAPSHOT  (daily log — the heart of VEKTRA)
# ─────────────────────────────────────────────
class Snapshot(Base):
    __tablename__ = 'snapshots'

    id          = Column(Integer,  primary_key=True, index=True)
    user_id     = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    timestamp   = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    log_date    = Column(Date,     nullable=True, index=True)   # the actual day this log is for
    locked      = Column(Boolean,  default=False)               # locks at midnight — no edits after

    # ── MENTAL & EMOTIONAL ────────────────────
    mood_score              = Column(Integer, nullable=True)    # 1-10
    energy_level            = Column(Integer, nullable=True)    # 1-10
    focus_level             = Column(Integer, nullable=True)    # 1-10
    social_battery          = Column(Integer, nullable=True)    # 1-10
    health_battery          = Column(Integer, nullable=True)    # 1-10
    uncomfortable_moments   = Column(Text,    nullable=True)    # what made you uneasy + reaction
    future_self_message     = Column(Text,    nullable=True)    # weekly — note to future self
    ai_accuracy             = Column(Integer, nullable=True)    # 1-10 — was AI report accurate

    # ── BODY & HEALTH ─────────────────────────
    sleep_hours             = Column(Float,   nullable=True)    # 0-24
    body_weight             = Column(Float,   nullable=True)    # kg — weekly
    diet_taken              = Column(Text,    nullable=True)    # what you ate + how body felt
    screen_time             = Column(Float,   nullable=True)    # hours on devices

    # ── FINANCE ───────────────────────────────
    daily_income            = Column(Float,   nullable=True)    # all money in today
    expenses                = Column(Float,   nullable=True)    # all money out today
    savings_investments     = Column(Float,   nullable=True)    # saved or invested today
    current_net_worth       = Column(Float,   nullable=True)    # updated weekly
    current_capital         = Column(Float,   nullable=True)    # liquid cash available — weekly
    any_emergency           = Column(Text,    nullable=True)    # unexpected expense description
    emergency_amount        = Column(Float,   nullable=True)    # emergency cost in local currency

    # ── GOALS & DECISIONS ─────────────────────
    tomorrow_goal           = Column(Text,    nullable=True)    # top priority for tomorrow
    target_hit_and_why      = Column(Text,    nullable=True)    # did you hit yesterday's goal + reason
    target_hit_bool         = Column(Boolean, nullable=True)    # true/false — did you hit it
    best_decision           = Column(Text,    nullable=True)    # best call made today
    worst_decision          = Column(Text,    nullable=True)    # biggest mistake today
    lessons_learned         = Column(Text,    nullable=True)    # what went wrong + lesson
    what_i_avoided          = Column(Text,    nullable=True)    # tasks dodged + reason + plan
    risk_taken              = Column(Text,    nullable=True)    # risks accepted today

    # ── LEARNING & GROWTH ─────────────────────
    skills_learned          = Column(Text,    nullable=True)    # knowledge gained today
    new_ideas               = Column(Text,    nullable=True)    # ideas generated — captured before lost
    interactions_done       = Column(Text,    nullable=True)    # key human interactions today
    interaction_outcome     = Column(Text,    nullable=True)    # did those interactions work
    gratitude_line          = Column(Text,    nullable=True)    # one thing grateful for
    funny_line              = Column(Text,    nullable=True)    # something that made you laugh
    quotes_insights         = Column(Text,    nullable=True)    # quote + source

    # ── PERFORMANCE & FOCUS ───────────────────
    focus_hours             = Column(Float,   nullable=True)    # deep work hours — hard number
    environment_rating      = Column(Integer, nullable=True)    # 1-10 quality of work environment
    opportunity_cost        = Column(Float,   nullable=True)    # hours wasted on low value tasks

    # ── WEEKLY INPUTS (logged once per week) ──
    how_many_goals          = Column(Integer, nullable=True)    # active goals count — auto computed
    decision_speed          = Column(Float,   nullable=True)    # avg hours to make decisions this week
    goal_intensity          = Column(JSON,    nullable=True)    # {goal_id: intensity} per goal

    # ── COMPUTED BY APP (never filled manually) ──
    net_worth_variance      = Column(Float,   nullable=True)    # % change vs previous week
    burn_rate               = Column(Float,   nullable=True)    # daily spend rate (30 day avg)
    resilience_score        = Column(Float,   nullable=True)    # months survivable at zero income
    survival_runway         = Column(Float,   nullable=True)    # days survivable at current burn
    procrastination_delta   = Column(Float,   nullable=True)    # % of planned tasks avoided
    leverage_score          = Column(Float,   nullable=True)    # focus_hours / screen_time * mood
    system_leak             = Column(Float,   nullable=True)    # gap between planned vs actual output
    mistake_correlation     = Column(Float,   nullable=True)    # how fast mistakes follow low sleep/mood
    goal_completion_pct     = Column(Float,   nullable=True)    # % goals hit this week
    opportunity_cost_score  = Column(Float,   nullable=True)    # % time wasted on low value tasks
    vektra_score            = Column(Float,   nullable=True)    # THE master trajectory score 0-100

    # ── OVERFLOW (any extra fields) ───────────
    data                    = Column(JSON,    nullable=True)    # catch-all for future fields

    user = relationship('User', back_populates='snapshots')


# ─────────────────────────────────────────────
#  REPORT
# ─────────────────────────────────────────────
class Report(Base):
    __tablename__ = 'reports'

    id              = Column(Integer,  primary_key=True, index=True)
    user_id         = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    generated_at    = Column(DateTime, default=datetime.datetime.utcnow)
    period_start    = Column(DateTime, nullable=True)
    period_end      = Column(DateTime, nullable=True)

    report_type     = Column(String(20), nullable=False, default='weekly')  # weekly/monthly/quarterly/annual/birthday/holiday
    status          = Column(String(20), nullable=False, default='pending') # pending/ready/expired
    expires_at      = Column(DateTime,   nullable=True)                     # when report expires by tier

    # ── content ───────────────────────────────
    content         = Column(JSON,   nullable=True)     # full structured report data
    summary_text    = Column(Text,   nullable=True)     # AI narrative summary
    vektra_score    = Column(Float,  nullable=True)     # score at time of report

    # ── formats available ─────────────────────
    link_url        = Column(String(500), nullable=True)  # shareable link
    image_urls      = Column(JSON,        nullable=True)  # list of image URLs by resolution
    pdf_url         = Column(String(500), nullable=True)  # PDF download link
    video_url       = Column(String(500), nullable=True)  # video report link

    # ── delivery ──────────────────────────────
    delivered       = Column(Boolean,  default=False)
    opened          = Column(Boolean,  default=False)
    opened_at       = Column(DateTime, nullable=True)

    user = relationship('User', back_populates='reports')


# ─────────────────────────────────────────────
#  SUBSCRIPTION
# ─────────────────────────────────────────────
class Subscription(Base):
    __tablename__ = 'subscriptions'

    id                      = Column(Integer,  primary_key=True, index=True)
    user_id                 = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at              = Column(DateTime, default=datetime.datetime.utcnow)

    provider                = Column(String(50),  nullable=False, default='stripe')  # stripe / mpesa
    provider_customer_id    = Column(String(255), nullable=True)
    plan                    = Column(String(50),  nullable=True)   # free/tier1/tier2/tier3
    duration_days           = Column(Integer,     nullable=True)   # chosen duration from slider
    discount_pct            = Column(Float,       nullable=True)   # applied discount %
    days_free               = Column(Integer,     nullable=True)   # free days earned
    amount_paid             = Column(Float,       nullable=True)   # final amount paid
    currency                = Column(String(10),  nullable=True, default='USD')
    active                  = Column(Boolean,     default=True)
    starts_at               = Column(DateTime,    nullable=True)
    expires_at              = Column(DateTime,    nullable=True)

    user = relationship('User', back_populates='subscriptions')


# ─────────────────────────────────────────────
#  PAYMENT
# ─────────────────────────────────────────────
class Payment(Base):
    __tablename__ = 'payments'

    id                      = Column(Integer,  primary_key=True, index=True)
    user_id                 = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at              = Column(DateTime, default=datetime.datetime.utcnow)

    provider                = Column(String(50),  nullable=False)   # stripe / mpesa
    provider_customer_id    = Column(String(255), nullable=True)
    provider_payment_id     = Column(String(255), nullable=True)
    amount                  = Column(Float,       nullable=True)
    currency                = Column(String(10),  nullable=True, default='USD')
    status                  = Column(String(50),  nullable=False, default='pending')  # pending/succeeded/failed
    external_response       = Column(JSON,        nullable=True)

    user = relationship('User')


# ─────────────────────────────────────────────
#  VEK CREDITS  (referral reward system)
# ─────────────────────────────────────────────
class VekCredit(Base):
    __tablename__ = 'vek_credits'

    id              = Column(Integer,  primary_key=True, index=True)
    user_id         = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)

    amount          = Column(Integer,  nullable=False, default=0)   # credits earned
    reason          = Column(String(100), nullable=True)            # referral / welcome / promotion
    redeemed        = Column(Boolean,  default=False)
    redeemed_at     = Column(DateTime, nullable=True)
    redeemed_for    = Column(String(100), nullable=True)            # subscription_days / tier_upgrade

    user = relationship('User', back_populates='vek_credits')


# ─────────────────────────────────────────────
#  REFERRAL
# ─────────────────────────────────────────────
class Referral(Base):
    __tablename__ = 'referrals'

    id              = Column(Integer,  primary_key=True, index=True)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow)

    referrer_id     = Column(Integer,  ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    referred_email  = Column(String(255), nullable=True)            # who was invited
    referred_user_id= Column(Integer,  ForeignKey('users.id', ondelete='SET NULL'), nullable=True)  # set when they join
    converted       = Column(Boolean,  default=False)               # true when they pay
    converted_at    = Column(DateTime, nullable=True)
    tier_purchased  = Column(String(20), nullable=True)             # which tier they bought
    credits_awarded = Column(Integer,  default=0)                   # credits given to referrer

    referrer        = relationship('User', foreign_keys=[referrer_id], back_populates='referrals_made')