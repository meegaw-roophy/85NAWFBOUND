"""add goals table

Revision ID: 0002_add_goals
Revises: 0001_initial
Create Date: 2026-06-04
"""
from alembic import op
import sqlalchemy as sa

revision = '0002_add_goals'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'goals',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('category', sa.Enum('financial', 'wellness', 'career', 'education', 'fitness', 'custom', name='goalcategory'), nullable=False, server_default='custom'),
        sa.Column('status', sa.Enum('active', 'completed', 'paused', 'cancelled', name='goalstatus'), nullable=False, server_default='active'),
        sa.Column('target_value', sa.Float, nullable=True),
        sa.Column('current_value', sa.Float, server_default='0'),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('deadline', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index('ix_goals_id', 'goals', ['id'])
    op.create_index('ix_goals_user_id', 'goals', ['user_id'])


def downgrade():
    op.drop_index('ix_goals_user_id', 'goals')
    op.drop_index('ix_goals_id', 'goals')
    op.drop_table('goals')
    op.execute("DROP TYPE IF EXISTS goalcategory")
    op.execute("DROP TYPE IF EXISTS goalstatus")
