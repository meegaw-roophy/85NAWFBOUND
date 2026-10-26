"""add cashpool, XP points and snapshot expense categories

Revision ID: add_cashpool_and_xp
Revises: drop_users_full_name
Create Date: 2026-10-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_cashpool_and_xp'
down_revision = 'drop_users_full_name'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('snapshots', sa.Column('expense_category', sa.String(50), nullable=True))

    op.create_table(
        'cashpools',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('target_savings_rate', sa.Float(), nullable=True),
        sa.Column('current_savings_rate', sa.Float(), nullable=True),
        sa.Column('total_savings', sa.Float(), nullable=True),
        sa.Column('target_monthly_savings', sa.Float(), nullable=True),
        sa.Column('daily_spend_cap', sa.Float(), nullable=True),
        sa.Column('weekly_spend_cap', sa.Float(), nullable=True),
        sa.Column('monthly_spend_cap', sa.Float(), nullable=True),
        sa.Column('cap_breach_count', sa.Integer(), nullable=True),
        sa.Column('last_cap_breach_at', sa.DateTime(), nullable=True),
        sa.Column('current_runway_days', sa.Float(), nullable=True),
        sa.Column('target_runway_days', sa.Float(), nullable=True),
        sa.Column('runway_warning_sent', sa.Boolean(), nullable=True),
        sa.Column('emergency_fund_target', sa.Float(), nullable=True),
        sa.Column('emergency_fund_current', sa.Float(), nullable=True),
        sa.Column('emergency_fund_met', sa.Boolean(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_income', sa.Float(), nullable=True),
        sa.Column('period_expenses', sa.Float(), nullable=True),
        sa.Column('period_savings', sa.Float(), nullable=True),
        sa.Column('period_days_logged', sa.Integer(), nullable=True),
        sa.Column('alert_on_cap_breach', sa.Boolean(), nullable=True),
        sa.Column('alert_on_low_runway', sa.Boolean(), nullable=True),
        sa.Column('alert_on_savings_miss', sa.Boolean(), nullable=True),
    )

    op.create_table(
        'user_points',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('total_points', sa.Integer(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=True),
        sa.Column('points_to_next', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'point_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_point_transactions_user_id', 'point_transactions', ['user_id'])


def downgrade():
    op.drop_index('ix_point_transactions_user_id', table_name='point_transactions')
    op.drop_table('point_transactions')
    op.drop_table('user_points')
    op.drop_table('cashpools')
    op.drop_column('snapshots', 'expense_category')
