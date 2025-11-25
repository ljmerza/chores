from datetime import date
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.models import User
from households.models import (
    Household,
    HouseholdMembership,
    Leaderboard,
    PointTransaction,
    UserScore,
)


class HouseholdModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")

    def test_invite_code_regenerates_on_collision(self):
        """
        Ensure invite codes retry when a collision occurs.
        """
        with patch(
            "households.models.generate_invite_code",
            side_effect=["DUPLICAT", "DUPLICAT", "NEWCODE1"],
        ):
            first = Household.objects.create(name="Home A", created_by=self.user)
            second = Household.objects.create(name="Home B", created_by=self.user)

        self.assertEqual(first.invite_code, "DUPLICAT")
        self.assertEqual(second.invite_code, "NEWCODE1")

    def test_user_score_disallows_negative_points(self):
        household = Household.objects.create(name="Home", created_by=self.user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserScore.objects.create(
                    user=self.user,
                    household=household,
                    current_points=-1,
                    lifetime_points=0,
                )

    def test_point_transaction_requires_non_negative_balance(self):
        household = Household.objects.create(name="Home", created_by=self.user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PointTransaction.objects.create(
                    user=self.user,
                    household=household,
                    transaction_type="earned",
                    amount=5,
                    balance_after=-1,
                    source_type="manual",
                    source_id=None,
                    description="Invalid balance",
                    created_by=self.user,
                )

    def test_leaderboard_enforces_non_negative_fields(self):
        household = Household.objects.create(name="Home", created_by=self.user)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Leaderboard.objects.create(
                    household=household,
                    user=self.user,
                    period="weekly",
                    period_start_date=date.today(),
                    points=-10,
                    chores_completed=1,
                    rank=1,
                )


class ManageHouseholdViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_admin",
            email="owner@example.com",
            password="Str0ngPass!",
            role="admin",
            first_name="Owner",
        )
        self.household = Household.objects.create(name="Home", created_by=self.owner)
        self.owner_membership = HouseholdMembership.objects.create(
            household=self.household,
            user=self.owner,
            role="admin",
        )
        UserScore.objects.create(user=self.owner, household=self.household)
        self.url = reverse("manage_household")

    def test_member_cannot_access_manage(self):
        member = User.objects.create_user(username="member_one", email="member@example.com", password="pass")
        HouseholdMembership.objects.create(
            household=self.household,
            user=member,
            role="member",
        )

        self.client.force_login(member)
        response = self.client.get(self.url, {"household": self.household.id})
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("home"), response.url)

    def test_admin_updates_details(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {
                "action": "update_details",
                "household_id": self.household.id,
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.household.refresh_from_db()
        self.assertEqual(self.household.name, "Updated Name")
        self.assertEqual(self.household.description, "Updated description")

    def test_invite_member_creates_user_and_score(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {
                "action": "invite_member",
                "household_id": self.household.id,
                "first_name": "New",
                "last_name": "Member",
                "username": "newmember",
                "email": "new@example.com",
                "role": "member",
                "password": "TempPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="new@example.com")
        self.assertTrue(
            HouseholdMembership.objects.filter(
                household=self.household, user=user, role="member"
            ).exists()
        )
        self.assertTrue(
            UserScore.objects.filter(household=self.household, user=user).exists()
        )

    def test_cannot_remove_last_admin(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {
                "action": "remove_member",
                "household_id": self.household.id,
                "membership_id": self.owner_membership.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            HouseholdMembership.objects.filter(
                id=self.owner_membership.id
            ).exists()
        )

    def test_change_role_when_multiple_admins(self):
        second_admin = User.objects.create_user(
            username="second_admin",
            email="second@example.com",
            password="Str0ngPass!",
            role="admin",
        )
        HouseholdMembership.objects.create(
            household=self.household,
            user=second_admin,
            role="admin",
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {
                "action": "change_role",
                "household_id": self.household.id,
                "membership_id": self.owner_membership.id,
                "role": "member",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.owner_membership.refresh_from_db()
        self.assertEqual(self.owner_membership.role, "member")

    def test_regenerate_invite_code(self):
        self.client.force_login(self.owner)
        old_code = self.household.invite_code
        response = self.client.post(
            self.url,
            {
                "action": "regenerate_invite",
                "household_id": self.household.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.household.refresh_from_db()
        self.assertNotEqual(old_code, self.household.invite_code)
