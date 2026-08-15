"""add oauth provider fields

Revision ID: oauth_fields
Revises: report_sharing_fields
Create Date: 2024-08-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'oauth_fields'
down_revision = 'report_sharing_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('oauth_access_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_refresh_token', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('oauth_token_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('users', 'oauth_token_expires_at')
    op.drop_column('users', 'oauth_refresh_token')
    op.drop_column('users', 'oauth_access_token')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
