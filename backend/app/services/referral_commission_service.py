"""
Referral Commission Service
============================
Turns a referred user's own successful payment into a real-money commission
for whoever referred them - a declining percentage of that specific referred
person's 1st through 4th payment (22% / 16.5% / 11% / 5.5%, then 0%). Resets
per referred user, not per the referrer's lifetime referral count.

"available" (withdrawable) is never a stored status - it's computed at read
time in crud.get_referral_wallet_balances(), since a commission can flip back
out of "available" the moment a refund request opens on its triggering
payment, even after its hold period has technically elapsed. See the
docstring there for the exact rule.
"""

import datetime
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Referral, ReferralCommission, Payment
from app import crud

RATE_SCHEDULE = {1: 0.22, 2: 0.165, 3: 0.11, 4: 0.055}  # 5+ -> no row created at all


async def create_commission_for_payment(db: AsyncSession, payment: Payment) -> Optional[ReferralCommission]:
    """
    Called right after a Payment transitions to status='succeeded' (see the
    already_succeeded transition guard in webhooks.py - this must only ever
    be called once per payment). Safe to call speculatively on every
    succeeded payment: it's a no-op whenever the payer wasn't referred.
    """
    # 1. Was this payer ever referred? Don't gate on Referral.converted - it's
    # hardcoded True at signup time already (a pre-existing, separate bug),
    # so it carries no payment-time signal at all.
    referral_result = await db.execute(
        select(Referral).where(Referral.referred_user_id == payment.user_id)
    )
    referral = referral_result.scalars().first()
    if not referral:
        return None

    # 2. Idempotency - the DB unique constraint on payment_id is the hard
    # backstop, this is just a clean early return for the common case.
    existing_result = await db.execute(
        select(ReferralCommission).where(ReferralCommission.payment_id == payment.id)
    )
    if existing_result.scalars().first():
        return None

    # 3. Sequence number = how many succeeded payments THIS referred user has
    # ever made, counting the one just committed (naturally 1-indexed since
    # signup itself never creates a Payment row).
    count_result = await db.execute(
        select(func.count(Payment.id))
        .where(Payment.user_id == payment.user_id)
        .where(Payment.status == 'succeeded')
    )
    sequence_number = count_result.scalar() or 1

    rate = RATE_SCHEDULE.get(sequence_number)
    if rate is None:
        return None  # 5th+ payment from this referred user - no commission, no row

    succeeded_at = payment.succeeded_at or payment.created_at or datetime.datetime.utcnow()
    commission_amount = round((payment.amount or 0.0) * rate, 2)

    commission = ReferralCommission(
        referral_id=referral.id,
        referrer_id=referral.referrer_id,
        referred_user_id=payment.user_id,
        payment_id=payment.id,
        sequence_number=sequence_number,
        commission_rate=rate,
        commission_amount=commission_amount,
        currency=payment.currency or 'USD',
        status='pending',
        available_at=succeeded_at + datetime.timedelta(days=settings.REFERRAL_COMMISSION_HOLD_DAYS),
    )
    db.add(commission)

    # Flat bonus credit "gift" on top of the real cash - not tuned, founder
    # explicitly said just gift them for now.
    await crud.create_vek_credit(
        db,
        referral.referrer_id,
        amount=settings.REFERRAL_COMMISSION_BONUS_CREDITS,
        reason='referral-commission-bonus',
    )

    await db.commit()
    await db.refresh(commission)
    return commission


def usd_equivalent(amount: float, currency: str, fx_rates: dict) -> float:
    """Convert amount in `currency` to its USD-equivalent using FX rates
    already built for pricing (app.api.v1.pricing.get_fx_rates). Used ONLY
    for threshold checks (e.g. the $10-equivalent minimum withdrawal) - the
    actual commission/payout amount is never converted, ever."""
    rate = fx_rates.get(currency, 1.0) or 1.0
    return amount / rate
