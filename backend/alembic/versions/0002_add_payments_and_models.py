"""add payments and additional models

Revision ID: 0002_add_payments_and_models
Revises: 0001_initial
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_payments_and_models'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'snapshots',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=True),
        sa.Column('data', sa.JSON, nullable=True),
        sa.Column('mood', sa.Integer, nullable=True),
        sa.Column('energy', sa.Integer, nullable=True),
        sa.Column('focus', sa.Integer, nullable=True),
        sa.Column('income', sa.Float, nullable=True),
        sa.Column('expenses', sa.Float, nullable=True),
        sa.Column('savings', sa.Float, nullable=True),
    )

    op.create_table(
        'reports',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('period_start', sa.DateTime, nullable=True),
        sa.Column('period_end', sa.DateTime, nullable=True),
        sa.Column('generated_at', sa.DateTime, nullable=True),
        sa.Column('content', sa.JSON, nullable=True),
        sa.Column('summary_text', sa.String, nullable=True),
    )

    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, default='stripe'),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('plan', sa.String(length=255), nullable=True),
        sa.Column('active', sa.Boolean, nullable=True, server_default=sa.sql.expression.true()),
        sa.Column('created_at', sa.DateTime, nullable=True),
    )

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Float, nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('external_response', sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=True),
    )


def downgrade():
    op.drop_table('payments')
    op.drop_table('subscriptions')
    op.drop_table('reports')
    op.drop_table('snapshots')
