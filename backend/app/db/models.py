from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Float, Boolean, Enum as SAEnum
from sqlalchemy.orm import declarative_base, relationship
import datetime
import enum

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    snapshots = relationship('Snapshot', back_populates='user')
    reports = relationship('Report', back_populates='user')
    subscriptions = relationship('Subscription', back_populates='user')
    goals = relationship('Goal', back_populates='user')


class Snapshot(Base):
    __tablename__ = 'snapshots'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    data = Column(JSON, nullable=True)

    # common quick fields
    mood = Column(Integer, nullable=True)
    energy = Column(Integer, nullable=True)
    focus = Column(Integer, nullable=True)
    income = Column(Float, nullable=True)
    expenses = Column(Float, nullable=True)
    savings = Column(Float, nullable=True)

    user = relationship('User', back_populates='snapshots')


class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow)
    content = Column(JSON, nullable=True)  # store structured report
    summary_text = Column(String, nullable=True)

    user = relationship('User', back_populates='reports')


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = Column(String(50), nullable=False, default='stripe')
    provider_customer_id = Column(String(255), nullable=True)
    plan = Column(String(255), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User', back_populates='subscriptions')


class GoalCategory(str, enum.Enum):
    financial = "financial"
    wellness = "wellness"
    career = "career"
    education = "education"
    fitness = "fitness"
    custom = "custom"


class GoalStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    paused = "paused"
    cancelled = "cancelled"


class Goal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    category = Column(SAEnum(GoalCategory), default=GoalCategory.custom, nullable=False)
    status = Column(SAEnum(GoalStatus), default=GoalStatus.active, nullable=False)
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, default=0.0)
    unit = Column(String(50), nullable=True)  # e.g., "$", "kg", "hours"
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship('User', back_populates='goals')
