"""add email verification and password reset fields

Revision ID: email_verify_reset
Revises: add_weekly_monthly_questions
Create Date: 2024-08-14

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timedelta

# revision identifiers, used by Alembic.
revision = 'email_verify_reset'
down_revision = 'add_weekly_monthly_questions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), default=False, nullable=True))
    op.add_column('users', sa.Column('verification_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('verification_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('reset_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'reset_expires_at')
    op.drop_column('users', 'reset_token')
    op.drop_column('users', 'verification_expires_at')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'is_verified')
