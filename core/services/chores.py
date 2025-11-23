from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from core.models import User
from core.services.notifications import create_notification
from core.services.points import PointChangeResult, adjust_points
from chores.models import ChoreInstance


class ChoreStateError(Exception):
    """Raised when an invalid state transition is attempted."""


class MissingAssigneeError(Exception):
    """Raised when a chore instance cannot determine an assignee/claimer."""


@dataclass
class ChoreCompletionResult:
    instance: ChoreInstance
    points_result: PointChangeResult


def complete_chore_instance(
    *,
    instance: ChoreInstance,
    completed_by: User,
    points_awarded: Optional[int] = None,
    completion_notes: Optional[str] = None,
) -> ChoreCompletionResult:
    """
    Mark a ChoreInstance as completed, award points, and notify the assignee/claimer.
    """
    if instance.status not in ("available", "claimed", "in_progress"):
        raise ChoreStateError(f"Cannot complete chore in state '{instance.status}'.")

    assignee = instance.assigned_user or completed_by
    if assignee is None:
        raise MissingAssigneeError("Chore completion requires an assignee or claimer.")

    awarded_points = points_awarded if points_awarded is not None else instance.chore.base_points
    if awarded_points < 0:
        raise ChoreStateError("Points awarded cannot be negative.")

    now = timezone.now()

    with transaction.atomic():
        instance.status = "completed"
        instance.completed_at = instance.completed_at or now
        instance.points_awarded = awarded_points
        if completion_notes:
            instance.completion_notes = completion_notes
        instance.save(
            update_fields=[
                "status",
                "completed_at",
                "points_awarded",
                "completion_notes",
            ]
        )

        points_result = adjust_points(
            user=assignee,
            household=instance.chore.household,
            amount=awarded_points,
            transaction_type="earned",
            source_type="chore",
            source_id=instance.id,
            description=f"Chore completed: {instance.chore.title}",
            increment_completed=True,
            completed_at=instance.completed_at,
        )

    create_notification(
        user=assignee,
        household=instance.chore.household,
        notification_type="points_awarded",
        title="Chore completed",
        message=f"You earned {awarded_points} points for '{instance.chore.title}'.",
        link="",
    )

    return ChoreCompletionResult(instance=instance, points_result=points_result)
