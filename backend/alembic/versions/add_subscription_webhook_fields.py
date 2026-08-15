"""add subscription webhook and auto-renew fields

Revision ID: sub_webhook_fields
Revises: email_verify_reset
Create Date: 2024-08-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'sub_webhook_fields'
down_revision = 'email_verify_reset'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('subscriptions', sa.Column('provider_subscription_id', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('auto_renew', sa.Boolean(), default=False, nullable=True))
    op.add_column('subscriptions', sa.Column('webhook_url', sa.String(500), nullable=True))
    op.add_column('subscriptions', sa.Column('webhook_secret', sa.String(255), nullable=True))
    op.add_column('subscriptions', sa.Column('last_webhook_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('subscriptions', 'last_webhook_at')
    op.drop_column('subscriptions', 'webhook_secret')
    op.drop_column('subscriptions', 'webhook_url')
    op.drop_column('subscriptions', 'auto_renew')
    op.drop_column('subscriptions', 'provider_subscription_id')
