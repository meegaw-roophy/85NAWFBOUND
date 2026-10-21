"""drop unused users.full_name

Revision ID: drop_users_full_name
Revises: add_referral_commissions
Create Date: 2026-10-21

full_name was never shown anywhere (the app greets users by username) and
was already dropped by hand in production, so only drop it where it still
exists.

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'drop_users_full_name'
down_revision = 'add_referral_commissions'
branch_labels = None
depends_on = None


def _has_full_name():
    return 'full_name' in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')}


def upgrade():
    if _has_full_name():
        op.drop_column('users', 'full_name')


def downgrade():
    if not _has_full_name():
        op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))
