from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import User
from households.models import Household, PointTransaction, UserScore


class PointsError(Exception):
    """Base error for point operations."""


class InvalidAmountError(PointsError):
    """Raised when an invalid amount is provided."""


class NegativeBalanceError(PointsError):
    """Raised when an operation would result in negative balance."""


@dataclass
class PointChangeResult:
    score: UserScore
    transaction: PointTransaction


def adjust_points(
    *,
    user: User,
    household: Household,
    amount: int,
    transaction_type: str,
    source_type: str,
    source_id: Optional[int] = None,
    description: str = "",
    increment_completed: bool = False,
    completed_at=None,
) -> PointChangeResult:
    """
    Adjust a user's points within a household with validation and auditing.
    """
    if amount == 0:
        raise InvalidAmountError("Amount must be non-zero.")

    if transaction_type in ("earned", "bonus") and amount < 0:
        raise InvalidAmountError("Earned/bonus amounts must be positive.")
    if transaction_type == "spent" and amount > 0:
        raise InvalidAmountError("Spent amounts must be negative.")

    with transaction.atomic():
        score, _ = UserScore.objects.select_for_update().get_or_create(
            user=user, household=household
        )

        new_balance = score.current_points + amount
        if new_balance < 0:
            raise NegativeBalanceError("Insufficient points for this operation.")

        score.current_points = new_balance
        fields = ["current_points", "updated_at"]

        if amount > 0:
            score.lifetime_points = score.lifetime_points + amount
            fields.append("lifetime_points")

        if increment_completed:
            score.total_chores_completed += 1
            score.last_chore_completed_at = completed_at or timezone.now()
            fields.extend(["total_chores_completed", "last_chore_completed_at"])

        score.save(update_fields=fields)

        transaction_record = PointTransaction.objects.create(
            user=user,
            household=household,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            source_type=source_type,
            source_id=source_id,
            description=description or "",
            created_by=user,
        )

    return PointChangeResult(score=score, transaction=transaction_record)
