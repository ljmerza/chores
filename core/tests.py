from django.test import TestCase

from core.models import User
from core.services.points import (
    InvalidAmountError,
    NegativeBalanceError,
    adjust_points,
)
from households.models import Household


class PointsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
        self.household = Household.objects.create(name="Home", created_by=self.user)

    def test_award_points_updates_score_and_transaction(self):
        result = adjust_points(
            user=self.user,
            household=self.household,
            amount=10,
            transaction_type="earned",
            source_type="chore",
            source_id=1,
            description="Test award",
        )

        self.assertEqual(result.score.current_points, 10)
        self.assertEqual(result.score.lifetime_points, 10)
        self.assertEqual(result.transaction.amount, 10)
        self.assertEqual(result.transaction.balance_after, 10)

    def test_negative_balance_prevented(self):
        with self.assertRaises(NegativeBalanceError):
            adjust_points(
                user=self.user,
                household=self.household,
                amount=-5,
                transaction_type="spent",
                source_type="reward",
                source_id=1,
                description="Overspend",
            )

    def test_zero_amount_disallowed(self):
        with self.assertRaises(InvalidAmountError):
            adjust_points(
                user=self.user,
                household=self.household,
                amount=0,
                transaction_type="earned",
                source_type="chore",
                source_id=1,
            )
