from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.models import User
from households.models import HouseholdMembership, UserScore, PointTransaction
from .models import Reward, RewardRedemption


class RewardError(ValueError):
    """User-facing error for reward actions."""


def _require_membership(user, household):
    if not HouseholdMembership.objects.filter(user=user, household=household).exists():
        raise RewardError("You must be in this household to redeem rewards.")


def _get_score_for_update(user, household):
    score = (
        UserScore.objects.select_for_update()
        .filter(user=user, household=household)
        .first()
    )
    if not score:
        raise RewardError("No score found for this household.")
    return score


def _log_transaction(user, household, amount, balance_after, source_id, description, transaction_type):
    PointTransaction.objects.create(
        user=user,
        household=household,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=balance_after,
        source_type='reward',
        source_id=source_id,
        description=description,
        created_by=user if transaction_type == 'earned' else None,
    )


def _check_limits(user, reward):
    now = timezone.now()
    active_statuses = ['pending', 'approved', 'fulfilled']

    if reward.per_user_limit:
        current_count = RewardRedemption.objects.filter(
            reward=reward,
            user=user,
            status__in=active_statuses,
        ).count()
        if current_count >= reward.per_user_limit:
            raise RewardError("You have reached the limit for this reward.")

    if reward.cooldown_days:
        window_start = now - timedelta(days=reward.cooldown_days)
        recent = RewardRedemption.objects.filter(
            reward=reward,
            user=user,
            status__in=active_statuses,
            created_at__gte=window_start,
        ).exists()
        if recent:
            raise RewardError("You need to wait before redeeming this reward again.")


def _apply_stock_delta(reward, delta):
    if reward.quantity_remaining is None:
        return
    new_qty = reward.quantity_remaining + delta
    if new_qty < 0:
        raise RewardError("This reward is out of stock.")
    reward.quantity_remaining = new_qty
    reward.save(update_fields=['quantity_remaining', 'updated_at'])


@transaction.atomic
def request_redemption(user: User, reward: Reward, household, user_note: str | None = None):
    reward = Reward.objects.select_for_update().get(id=reward.id)
    _require_membership(user, household)

    if reward.household_id != getattr(household, 'id', household):
        raise RewardError("This reward belongs to a different household.")

    if reward.allowed_members.exists() and not reward.allowed_members.filter(id=user.id).exists():
        raise RewardError("You are not eligible for this reward.")

    now = timezone.now()
    if not reward.is_active:
        raise RewardError("This reward is not active.")
    if reward.available_from and now < reward.available_from:
        raise RewardError("This reward is not available yet.")
    if reward.available_until and now > reward.available_until:
        raise RewardError("This reward is no longer available.")
    if reward.quantity_remaining is not None and reward.quantity_remaining <= 0:
        raise RewardError("This reward is out of stock.")

    _check_limits(user, reward)

    # Child accounts always require approval.
    requires_approval = reward.requires_approval or user.role == 'child'
    score = _get_score_for_update(user, household)
    if (score.current_points or 0) < reward.point_cost:
        raise RewardError("Not enough points.")

    score.current_points -= reward.point_cost
    score.save(update_fields=['current_points', 'updated_at'])

    redemption_status = 'pending'
    processed_by = None
    processed_at = None

    if not requires_approval:
        redemption_status = 'approved'
        processed_by = user
        processed_at = now
        _apply_stock_delta(reward, -1)

    redemption = RewardRedemption.objects.create(
        reward=reward,
        user=user,
        household=household,
        points_spent=reward.point_cost,
        status=redemption_status,
        user_note=user_note or '',
        processed_by=processed_by,
        processed_at=processed_at,
    )

    _log_transaction(
        user=user,
        household=household,
        amount=-reward.point_cost,
        balance_after=score.current_points,
        source_id=redemption.id,
        description=f"Redeemed {reward.title}",
        transaction_type='spent',
    )

    return redemption


@transaction.atomic
def approve_redemption(redemption: RewardRedemption, actor: User, decision_note: str | None = None):
    redemption = RewardRedemption.objects.select_for_update().select_related('reward', 'household').get(id=redemption.id)
    reward = Reward.objects.select_for_update().get(id=redemption.reward_id)

    if redemption.status != 'pending':
        raise RewardError("Only pending redemptions can be approved.")

    if reward.quantity_remaining is not None and reward.quantity_remaining <= 0:
        raise RewardError("This reward is out of stock.")

    _apply_stock_delta(reward, -1)

    redemption.status = 'approved'
    redemption.processed_by = actor
    redemption.processed_at = timezone.now()
    redemption.decision_note = decision_note or ''
    redemption.save(update_fields=['status', 'processed_by', 'processed_at', 'decision_note', 'fulfilled_at', 'refunded_at'])
    return redemption


@transaction.atomic
def deny_redemption(redemption: RewardRedemption, actor: User, reason: str | None = None, refund: bool = True):
    redemption = RewardRedemption.objects.select_for_update().select_related('reward', 'household', 'user').get(id=redemption.id)
    reward = Reward.objects.select_for_update().get(id=redemption.reward_id)
    score = _get_score_for_update(redemption.user, redemption.household)

    if redemption.status not in ['pending', 'approved']:
        raise RewardError("Only pending or approved redemptions can be denied.")

    if redemption.status == 'approved':
        _apply_stock_delta(reward, 1)

    if refund and not redemption.is_refunded:
        score.current_points += redemption.points_spent
        score.save(update_fields=['current_points', 'updated_at'])
        _log_transaction(
            user=redemption.user,
            household=redemption.household,
            amount=redemption.points_spent,
            balance_after=score.current_points,
            source_id=redemption.id,
            description=f"Refund for {reward.title}",
            transaction_type='bonus',
        )
        redemption.refunded_at = timezone.now()

    redemption.status = 'denied'
    redemption.processed_by = actor
    redemption.processed_at = timezone.now()
    redemption.decision_note = reason or ''
    redemption.save(update_fields=['status', 'processed_by', 'processed_at', 'decision_note', 'refunded_at', 'fulfilled_at'])
    return redemption


@transaction.atomic
def fulfill_redemption(redemption: RewardRedemption, actor: User, note: str | None = None):
    redemption = RewardRedemption.objects.select_for_update().get(id=redemption.id)
    if redemption.status != 'approved':
        raise RewardError("Only approved redemptions can be fulfilled.")

    redemption.status = 'fulfilled'
    redemption.fulfilled_at = timezone.now()
    redemption.fulfilled_by = actor
    if note:
        redemption.decision_note = note
    redemption.save(update_fields=['status', 'fulfilled_at', 'fulfilled_by', 'decision_note'])
    return redemption


@transaction.atomic
def cancel_redemption(redemption: RewardRedemption, actor: User, refund: bool = True):
    redemption = RewardRedemption.objects.select_for_update().select_related('reward', 'household', 'user').get(id=redemption.id)
    reward = Reward.objects.select_for_update().get(id=redemption.reward_id)
    score = _get_score_for_update(redemption.user, redemption.household)

    if redemption.status not in ['pending', 'approved']:
        raise RewardError("Only pending or approved redemptions can be cancelled.")

    if redemption.status == 'approved':
        _apply_stock_delta(reward, 1)

    if refund and not redemption.is_refunded:
        score.current_points += redemption.points_spent
        score.save(update_fields=['current_points', 'updated_at'])
        _log_transaction(
            user=redemption.user,
            household=redemption.household,
            amount=redemption.points_spent,
            balance_after=score.current_points,
            source_id=redemption.id,
            description=f"Cancellation refund for {reward.title}",
            transaction_type='bonus',
        )
        redemption.refunded_at = timezone.now()

    redemption.status = 'cancelled'
    redemption.processed_by = actor
    redemption.processed_at = timezone.now()
    redemption.save(update_fields=['status', 'processed_by', 'processed_at', 'refunded_at', 'decision_note', 'fulfilled_at'])
    return redemption
