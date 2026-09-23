"""add device/os/browser/country/ip_prefix to landing_clicks

Revision ID: add_landing_click_device_geo
Revises: add_country_code
Create Date: 2026-09-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_landing_click_device_geo'
down_revision = 'add_country_code'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('landing_clicks', sa.Column('device_type', sa.String(20), nullable=True))
    op.add_column('landing_clicks', sa.Column('os', sa.String(30), nullable=True))
    op.add_column('landing_clicks', sa.Column('browser', sa.String(30), nullable=True))
    op.add_column('landing_clicks', sa.Column('country', sa.String(60), nullable=True))
    op.add_column('landing_clicks', sa.Column('ip_prefix', sa.String(20), nullable=True))


def downgrade():
    op.drop_column('landing_clicks', 'ip_prefix')
    op.drop_column('landing_clicks', 'country')
    op.drop_column('landing_clicks', 'browser')
    op.drop_column('landing_clicks', 'os')
    op.drop_column('landing_clicks', 'device_type')
