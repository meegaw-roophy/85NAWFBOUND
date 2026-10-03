"""
Referral Commission API
========================
Real-money referral earnings for the referrer. See
app.services.referral_commission_service for how a commission actually gets
created (triggered from the Paystack webhook, not from here).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.deps import get_current_user
from app.core.config import settings
from app.schemas import ReferralWalletOut, ReferralStatsOut, WalletBalance, WithdrawalRequestCreate, WithdrawalRequestOut
from app.services.referral_commission_service import usd_equivalent
from app.api.v1.pricing import get_fx_rates
from app import crud

router = APIRouter(tags=["referral"])


def _check_ownership(current_user, user_id: int):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")


@router.get("/stats", response_model=ReferralStatsOut)
async def get_referral_stats(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_ownership(current_user, user_id)
    stats = await crud.get_referral_stats(db, user_id)
    return ReferralStatsOut(**stats)


@router.get("/wallet", response_model=ReferralWalletOut)
async def get_referral_wallet(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_ownership(current_user, user_id)
    balances = await crud.get_referral_wallet_balances(db, user_id)
    return ReferralWalletOut(
        balances=[WalletBalance(currency=cur, **b) for cur, b in balances.items()],
        min_withdrawal_usd_equivalent=settings.REFERRAL_MIN_WITHDRAWAL_USD_EQUIVALENT,
    )


@router.get("/withdrawals", response_model=list[WithdrawalRequestOut])
async def list_my_withdrawals(
    user_id: int,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_ownership(current_user, user_id)
    return await crud.list_withdrawal_requests_for_user(db, user_id)


@router.post("/withdraw", response_model=WithdrawalRequestOut)
async def request_withdrawal(
    user_id: int,
    payload: WithdrawalRequestCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    _check_ownership(current_user, user_id)

    balances = await crud.get_referral_wallet_balances(db, user_id)
    bucket = balances.get(payload.currency)
    available = bucket['available'] if bucket else 0.0

    # The minimum is always expressed in USD-equivalent terms, converted per
    # currency ONLY for this threshold check - the claimed/paid amount itself
    # is never converted (see referral_commission_service.usd_equivalent).
    fx_rates = get_fx_rates()
    available_usd = usd_equivalent(available, payload.currency, fx_rates)
    if available_usd < settings.REFERRAL_MIN_WITHDRAWAL_USD_EQUIVALENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Available balance must be at least ${settings.REFERRAL_MIN_WITHDRAWAL_USD_EQUIVALENT:.2f} (USD-equivalent) to withdraw.",
        )

    withdrawal = await crud.claim_available_commissions_for_withdrawal(db, user_id, payload.currency)
    if not withdrawal:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing available to withdraw in that currency.")

    if payload.payout_destination:
        withdrawal.payout_destination = payload.payout_destination
        db.add(withdrawal)
        await db.commit()
        await db.refresh(withdrawal)

    return withdrawal
