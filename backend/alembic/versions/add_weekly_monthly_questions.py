"""add weekly and monthly questions tables

Revision ID: add_weekly_monthly_questions
Revises: bc71e483a562
Create Date: 2024-08-14

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_weekly_monthly_questions'
down_revision = 'bc71e483a562'
branch_labels = None
depends_on = None


def upgrade():
    # Weekly questions table
    op.create_table(
        'weekly_questions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow, nullable=True),
        sa.Column('week_number', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('biggest_win', sa.Text(), nullable=True),
        sa.Column('blockers', sa.Text(), nullable=True),
        sa.Column('next_week_focus', sa.Text(), nullable=True),
        sa.Column('satisfaction', sa.Integer(), nullable=True),
    )
    
    # Monthly questions table
    op.create_table(
        'monthly_questions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow, nullable=True),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('monthly_goal', sa.Text(), nullable=True),
        sa.Column('habits_to_build', sa.Text(), nullable=True),
        sa.Column('success_definition', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table('monthly_questions')
    op.drop_table('weekly_questions')
