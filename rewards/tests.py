from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import User
from households.models import Household
from rewards.models import Reward


class RewardModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="pass")
        self.household = Household.objects.create(name="Home", created_by=self.user)

    def test_quantity_remaining_defaults_to_available(self):
        reward = Reward.objects.create(
            household=self.household,
            title="Movie Night",
            point_cost=10,
            category="activity",
            quantity_available=3,
            created_by=self.user,
        )
        self.assertEqual(reward.quantity_remaining, 3)

    def test_quantity_remaining_cannot_exceed_available(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Reward.objects.create(
                    household=self.household,
                    title="Big Reward",
                    point_cost=15,
                    category="item",
                    quantity_available=5,
                    quantity_remaining=10,
                    created_by=self.user,
                )
