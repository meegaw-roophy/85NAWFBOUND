"""add provider_payment_id to payments

Revision ID: 0003_add_provider_payment_id
Revises: 0002_add_payments_and_models
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa

revision = '0003_add_provider_payment_id'
down_revision = '0002_add_payments_and_models'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('payments', sa.Column('provider_payment_id', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('payments', 'provider_payment_id')
