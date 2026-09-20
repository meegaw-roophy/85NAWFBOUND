"""add country_code to users

Revision ID: add_country_code
Revises: add_landing_clicks
Create Date: 2026-09-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_country_code'
down_revision = 'add_landing_clicks'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('country_code', sa.String(5), nullable=True))


def downgrade():
    op.drop_column('users', 'country_code')
