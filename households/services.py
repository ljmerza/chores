"""
Household management services for member operations.
"""
from dataclasses import dataclass

from django.db import transaction

from core.models import User
from households.models import Household, HouseholdMembership, UserScore


class MembershipError(Exception):
    """Base exception for membership operations."""
    pass


class LastAdminError(MembershipError):
    """Raised when trying to remove or demote the last admin."""
    pass


class MemberNotFoundError(MembershipError):
    """Raised when a membership doesn't exist."""
    pass


@dataclass
class MembershipResult:
    membership: HouseholdMembership
    user: User
    household: Household
    score: UserScore | None = None


def add_member(
    *,
    household: Household,
    user: User,
    role: str = 'member',
) -> MembershipResult:
    """
    Add a user to a household with score initialization.

    Args:
        household: The household to add the user to
        user: The user to add
        role: The role to assign (default: 'member')

    Returns:
        MembershipResult with the created membership and score

    Raises:
        MembershipError: If the user is already a member
    """
    with transaction.atomic():
        membership, created = HouseholdMembership.objects.get_or_create(
            household=household,
            user=user,
            defaults={'role': role},
        )

        if not created:
            raise MembershipError(f"User {user.username} is already a member of this household")

        score, _ = UserScore.objects.get_or_create(
            user=user,
            household=household,
            defaults={
                'current_points': 0,
                'lifetime_points': 0,
                'total_chores_completed': 0,
            },
        )

        return MembershipResult(
            membership=membership,
            user=user,
            household=household,
            score=score,
        )


def change_member_role(
    *,
    membership: HouseholdMembership,
    new_role: str,
    actor: User,
) -> MembershipResult:
    """
    Change a member's role with admin count validation.

    Args:
        membership: The membership to update
        new_role: The new role to assign
        actor: The user performing the action

    Returns:
        MembershipResult with the updated membership

    Raises:
        LastAdminError: If this would remove the last admin from the household
    """
    with transaction.atomic():
        household = membership.household

        # Prevent removing the last admin
        if new_role != 'admin' and membership.role == 'admin':
            admin_count = HouseholdMembership.objects.filter(
                household=household,
                role='admin',
            ).exclude(pk=membership.pk).count()

            if admin_count < 1:
                raise LastAdminError("Household must have at least one admin")

        membership.role = new_role
        membership.save(update_fields=['role'])

        # Sync user role if promoting to admin
        if new_role == 'admin' and membership.user.role != 'admin':
            membership.user.role = 'admin'
            membership.user.save(update_fields=['role'])

        return MembershipResult(
            membership=membership,
            user=membership.user,
            household=household,
        )


def remove_member(
    *,
    membership: HouseholdMembership,
    actor: User,
) -> None:
    """
    Remove a member from a household with role validation.

    Args:
        membership: The membership to remove
        actor: The user performing the action

    Raises:
        LastAdminError: If this would remove the last admin from the household
    """
    with transaction.atomic():
        # Prevent removing the last admin
        if membership.role == 'admin':
            admin_count = HouseholdMembership.objects.filter(
                household=membership.household,
                role='admin',
            ).exclude(pk=membership.pk).count()

            if admin_count < 1:
                raise LastAdminError("Cannot remove the last admin from a household")

        membership.delete()


def get_membership(
    *,
    household: Household,
    user: User,
) -> HouseholdMembership | None:
    """
    Get a user's membership in a household.

    Args:
        household: The household to check
        user: The user to check

    Returns:
        The membership if found, None otherwise
    """
    return HouseholdMembership.objects.filter(
        household=household,
        user=user,
    ).first()


def is_admin(
    *,
    household: Household,
    user: User,
) -> bool:
    """
    Check if a user is an admin of a household.

    Args:
        household: The household to check
        user: The user to check

    Returns:
        True if the user is an admin, False otherwise
    """
    if user.is_staff or user.role == 'admin':
        return True

    return HouseholdMembership.objects.filter(
        household=household,
        user=user,
        role='admin',
    ).exists()
