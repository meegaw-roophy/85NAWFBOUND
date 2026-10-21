"""restore users.full_name where it was dropped outside alembic

Revision ID: restore_users_full_name
Revises: add_referral_commissions
Create Date: 2026-10-21

The production users table lost full_name while alembic_version still
claimed head, so every SELECT on User (login included) failed with
UndefinedColumnError. Only re-adds the column when it is missing, so this
is a no-op on databases that never lost it.

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'restore_users_full_name'
down_revision = 'add_referral_commissions'
branch_labels = None
depends_on = None


def upgrade():
    columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')}
    if 'full_name' not in columns:
        op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))


def downgrade():
    # Nothing to undo: the column belongs to the original schema.
    pass
