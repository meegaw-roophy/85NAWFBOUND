"""add referral commissions, withdrawal requests, refund requests, payments.succeeded_at

Revision ID: add_referral_commissions
Revises: add_landing_click_device_geo
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa
import datetime

# revision identifiers, used by Alembic.
revision = 'add_referral_commissions'
down_revision = 'add_landing_click_device_geo'
branch_labels = None
depends_on = None


def upgrade():
    # ── payments.succeeded_at ──────────────────────────────
    op.add_column('payments', sa.Column('succeeded_at', sa.DateTime(), nullable=True))

    # Best-effort backfill: no real succeeded-timestamp exists historically,
    # so created_at is the closest available approximation for old rows.
    # Only matters going forward for new rows (webhooks.py sets it directly
    # going forward) - this just avoids every historical row having a null
    # clock-start if this feature ever needs to look backward.
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE payments SET succeeded_at = created_at WHERE status = 'succeeded' AND succeeded_at IS NULL")
    )

    # ── withdrawal_requests ─────────────────────────────────
    op.create_table(
        'withdrawal_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_at', sa.DateTime(), default=datetime.datetime.utcnow),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False, server_default='requested'),
        sa.Column('payout_destination', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('processed_by_admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_withdrawal_requests_user_id', 'withdrawal_requests', ['user_id'])
    op.create_index('ix_withdrawal_requests_status', 'withdrawal_requests', ['status'])

    # ── refund_requests ──────────────────────────────────────
    op.create_table(
        'refund_requests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requested_at', sa.DateTime(), default=datetime.datetime.utcnow),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='requested'),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('processed_by_admin_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
    )
    op.create_index('ix_refund_requests_user_id', 'refund_requests', ['user_id'])
    op.create_index('ix_refund_requests_payment_id', 'refund_requests', ['payment_id'])
    op.create_index('ix_refund_requests_status', 'refund_requests', ['status'])

    # ── referral_commissions ─────────────────────────────────
    op.create_table(
        'referral_commissions',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('created_at', sa.DateTime(), default=datetime.datetime.utcnow),
        sa.Column('referral_id', sa.Integer(), sa.ForeignKey('referrals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('referrer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('referred_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payment_id', sa.Integer(), sa.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('commission_rate', sa.Float(), nullable=False),
        sa.Column('commission_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('available_at', sa.DateTime(), nullable=False),
        sa.Column('voided_at', sa.DateTime(), nullable=True),
        sa.Column('voided_reason', sa.String(255), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('withdrawal_request_id', sa.Integer(), sa.ForeignKey('withdrawal_requests.id', ondelete='SET NULL'), nullable=True),
        sa.UniqueConstraint('payment_id', name='uq_referral_commissions_payment_id'),
    )
    op.create_index('ix_referral_commissions_created_at', 'referral_commissions', ['created_at'])
    op.create_index('ix_referral_commissions_referral_id', 'referral_commissions', ['referral_id'])
    op.create_index('ix_referral_commissions_referrer_id', 'referral_commissions', ['referrer_id'])
    op.create_index('ix_referral_commissions_referred_user_id', 'referral_commissions', ['referred_user_id'])
    op.create_index('ix_referral_commissions_payment_id', 'referral_commissions', ['payment_id'])
    op.create_index('ix_referral_commissions_status', 'referral_commissions', ['status'])
    op.create_index('ix_referral_commissions_withdrawal_request_id', 'referral_commissions', ['withdrawal_request_id'])


def downgrade():
    op.drop_table('referral_commissions')
    op.drop_table('refund_requests')
    op.drop_table('withdrawal_requests')
    op.drop_column('payments', 'succeeded_at')
