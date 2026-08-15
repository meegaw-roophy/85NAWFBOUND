"""add report sharing customization fields

Revision ID: report_sharing_fields
Revises: sub_webhook_fields
Create Date: 2024-08-14

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'report_sharing_fields'
down_revision = 'sub_webhook_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('reports', sa.Column('share_with_public', sa.Boolean(), default=False, nullable=True))
    op.add_column('reports', sa.Column('share_with_circles', sa.Boolean(), default=False, nullable=True))
    op.add_column('reports', sa.Column('share_anonymously', sa.Boolean(), default=False, nullable=True))
    op.add_column('reports', sa.Column('custom_message', sa.Text(), nullable=True))
    op.add_column('reports', sa.Column('share_theme', sa.String(20), default='dark', nullable=True))
    op.add_column('reports', sa.Column('share_password', sa.String(255), nullable=True))
    op.add_column('reports', sa.Column('share_expires_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('reports', 'share_expires_at')
    op.drop_column('reports', 'share_password')
    op.drop_column('reports', 'share_theme')
    op.drop_column('reports', 'custom_message')
    op.drop_column('reports', 'share_anonymously')
    op.drop_column('reports', 'share_with_circles')
    op.drop_column('reports', 'share_with_public')
