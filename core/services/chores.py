from dataclasses import dataclass
from typing import Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from core.models import User
from core.services.notifications import create_notification
from core.services.points import PointChangeResult, adjust_points
from chores.models import Chore, ChoreInstance, ChoreTemplate
from households.models import Household


class ChoreStateError(Exception):
    """Raised when an invalid state transition is attempted."""


class MissingAssigneeError(Exception):
    """Raised when a chore instance cannot determine an assignee/claimer."""


class ChoreClaimError(Exception):
    """Raised when a chore cannot be claimed."""


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


@dataclass
class ChoreClaimResult:
    chore: Chore
    user: User


def claim_global_chore(
    *,
    chore_id: int,
    user: User,
) -> ChoreClaimResult:
    """
    Atomically claim a global chore for a user.

    Args:
        chore_id: The ID of the chore to claim
        user: The user claiming the chore

    Returns:
        ChoreClaimResult with the claimed chore and user

    Raises:
        ChoreClaimError: If the chore is not available for claiming
    """
    with transaction.atomic():
        chore = Chore.objects.select_for_update().filter(
            pk=chore_id,
            assignment_type='global',
            status='pending',
        ).first()

        if not chore:
            raise ChoreClaimError("Chore is not available for claiming")

        chore.assigned_to = user
        chore.status = 'in_progress'
        chore.save(update_fields=['assigned_to', 'status'])

        return ChoreClaimResult(chore=chore, user=user)


def get_system_templates_grouped_by_category() -> Dict[str, List[ChoreTemplate]]:
    """
    Fetch system-wide templates and group by category display name.

    Returns:
        Dict mapping category display names to lists of ChoreTemplate objects.
    """
    templates = ChoreTemplate.objects.filter(
        household__isnull=True, is_public=True
    ).order_by('category', 'title')

    categories: Dict[str, List[ChoreTemplate]] = {}
    for template in templates:
        cat_name = dict(ChoreTemplate.CATEGORY_CHOICES).get(
            template.category, template.category
        )
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(template)

    return categories


def create_chores_from_templates(
    templates: List[ChoreTemplate],
    household: Household,
    created_by: User,
    assignment_type: str = 'global'
) -> List[Chore]:
    """
    Create Chore objects from a list of ChoreTemplate objects.

    Uses bulk_create for efficiency when creating many chores.

    Args:
        templates: List of ChoreTemplate instances to convert
        household: Household the chores belong to
        created_by: User creating the chores
        assignment_type: One of 'assigned', 'global', 'rotating' (default: 'global')

    Returns:
        List of created Chore objects
    """
    if not templates:
        return []

    chore_objects = [
        Chore(
            household=household,
            title=template.title,
            description=template.description,
            category=template.category,
            difficulty=template.difficulty,
            base_points=template.suggested_points,
            status='pending',
            assignment_type=assignment_type,
            assigned_to=None,
            created_by=created_by,
            due_date=None,
            recurrence_pattern='none',
            requires_verification=False,
            estimated_minutes=template.estimated_minutes,
            priority='medium',
        )
        for template in templates
    ]

    with transaction.atomic():
        created_chores = Chore.objects.bulk_create(chore_objects)

    return created_chores
