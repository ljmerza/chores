from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import User
from households.models import Household, UserScore


class HouseholdModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="pass")

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
