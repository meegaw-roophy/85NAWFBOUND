"""add landing_clicks table

Revision ID: add_landing_clicks
Revises: oauth_fields
Create Date: 2026-09-09

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'add_landing_clicks'
down_revision = 'oauth_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'landing_clicks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow, index=True),
        sa.Column('link', sa.String(100), nullable=False),
        sa.Column('referrer', sa.String(500), nullable=True),
        sa.Column('utm_source', sa.String(100), nullable=True),
        sa.Column('utm_medium', sa.String(100), nullable=True),
        sa.Column('utm_campaign', sa.String(100), nullable=True),
    )


def downgrade():
    op.drop_table('landing_clicks')
