from typing import List

from django.db import transaction

from .models import Chore, ChoreTemplate


def create_chores_from_templates(
    templates: List[ChoreTemplate],
    household,
    created_by,
    assignment_type: str = 'global'
) -> List[Chore]:
    """
    Create Chore objects from a list of ChoreTemplate objects.

    Args:
        templates: List of ChoreTemplate instances to convert
        household: Household the chores belong to
        created_by: User creating the chores
        assignment_type: One of 'assigned', 'global', 'rotating' (default: 'global')

    Returns:
        List of created Chore objects
    """
    chores = []

    with transaction.atomic():
        for template in templates:
            chore = Chore.objects.create(
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
            chores.append(chore)

    return chores
