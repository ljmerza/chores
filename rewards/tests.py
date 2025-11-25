from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from core.models import User
from households.models import Household, HouseholdMembership, UserScore, PointTransaction
from rewards.models import Reward, RewardRedemption, MAX_REWARD_POINT_COST
from rewards.services import (
    request_redemption,
    approve_redemption,
    deny_redemption,
    cancel_redemption,
    RewardError,
)


class RewardModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
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

    def test_point_cost_clean_validates_range(self):
        reward = Reward(
            household=self.household,
            title="Zero Cost Reward",
            point_cost=0,
            category="activity",
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            reward.full_clean()

        reward.point_cost = MAX_REWARD_POINT_COST + 1
        with self.assertRaises(ValidationError):
            reward.full_clean()


class RewardServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_admin",
            email="owner@example.com",
            password="pass",
            role="admin",
        )
        self.household = Household.objects.create(name="Home", created_by=self.owner)
        HouseholdMembership.objects.create(
            household=self.household,
            user=self.owner,
            role="admin",
        )
        self.score = UserScore.objects.create(
            user=self.owner,
            household=self.household,
            current_points=50,
            lifetime_points=50,
        )
        self.reward = Reward.objects.create(
            household=self.household,
            title="Movie Night",
            point_cost=20,
            category="activity",
            quantity_available=2,
            created_by=self.owner,
            requires_approval=True,
        )

    def test_request_redemption_deducts_points_and_creates_pending(self):
        redemption = request_redemption(self.owner, self.reward, self.household)
        self.score.refresh_from_db()
        self.reward.refresh_from_db()

        self.assertEqual(redemption.status, "pending")
        self.assertEqual(self.score.current_points, 30)
        self.assertEqual(PointTransaction.objects.filter(source_id=redemption.id).count(), 1)
        # Stock not decremented until approval when approval is required.
        self.assertEqual(self.reward.quantity_remaining, 2)

    def test_auto_approve_decrements_stock(self):
        self.reward.requires_approval = False
        self.reward.save()
        redemption = request_redemption(self.owner, self.reward, self.household)
        self.reward.refresh_from_db()
        self.assertEqual(redemption.status, "approved")
        self.assertEqual(self.reward.quantity_remaining, 1)

    def test_cannot_exceed_limit_or_stock(self):
        self.reward.per_user_limit = 1
        self.reward.save()
        request_redemption(self.owner, self.reward, self.household)
        with self.assertRaises(RewardError):
            request_redemption(self.owner, self.reward, self.household)

        self.reward.quantity_remaining = 0
        self.reward.save(update_fields=["quantity_remaining"])
        with self.assertRaises(RewardError):
            request_redemption(self.owner, self.reward, self.household)

    def test_approve_and_deny_flow(self):
        redemption = request_redemption(self.owner, self.reward, self.household)
        approve_redemption(redemption, actor=self.owner)
        redemption.refresh_from_db()
        self.reward.refresh_from_db()
        self.assertEqual(redemption.status, "approved")
        self.assertEqual(self.reward.quantity_remaining, 1)

        deny_redemption(redemption, actor=self.owner, reason="Out of stock", refund=True)
        redemption.refresh_from_db()
        self.score.refresh_from_db()
        self.reward.refresh_from_db()

        self.assertEqual(redemption.status, "denied")
        self.assertTrue(redemption.is_refunded)
        self.assertEqual(self.score.current_points, 50)
        self.assertEqual(self.reward.quantity_remaining, 2)

    def test_cancel_pending_refunds_points(self):
        redemption = request_redemption(self.owner, self.reward, self.household)
        cancel_redemption(redemption, actor=self.owner, refund=True)
        redemption.refresh_from_db()
        self.score.refresh_from_db()
        self.assertEqual(redemption.status, "cancelled")
        self.assertEqual(self.score.current_points, 50)

    def test_allowed_members_gatekeeping(self):
        allowed_user = User.objects.create_user(username="allowed_user", email="allowed@example.com", password="pass")
        blocked_user = User.objects.create_user(username="blocked_user", email="blocked@example.com", password="pass")
        HouseholdMembership.objects.create(household=self.household, user=allowed_user, role="member")
        HouseholdMembership.objects.create(household=self.household, user=blocked_user, role="member")
        UserScore.objects.create(user=allowed_user, household=self.household, current_points=50, lifetime_points=50)
        UserScore.objects.create(user=blocked_user, household=self.household, current_points=50, lifetime_points=50)
        self.reward.allowed_members.set([allowed_user])

        # Allowed member can redeem
        redemption = request_redemption(allowed_user, self.reward, self.household)
        self.assertEqual(redemption.status, "pending")

        # Blocked member cannot redeem
        with self.assertRaises(RewardError):
            request_redemption(blocked_user, self.reward, self.household)


class CreateRewardViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner_admin",
            email="owner@example.com",
            password="pass",
            role="admin",
        )
        self.household = Household.objects.create(name="Home", created_by=self.owner)
        HouseholdMembership.objects.create(
            household=self.household,
            user=self.owner,
            role="admin",
        )
        self.url = reverse("create_reward")

    def test_admin_can_load_create_reward(self):
        self.client.force_login(self.owner)
        response = self.client.get(f"{self.url}?household={self.household.id}")
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_load_create_reward(self):
        member = User.objects.create_user(username="member_user", email="member@example.com", password="pass")
        HouseholdMembership.objects.create(
            household=self.household,
            user=member,
            role="member",
        )
        self.client.force_login(member)
        response = self.client.get(f"{self.url}?household={self.household.id}")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("home"), response.url)

    def test_admin_creates_reward(self):
        self.client.force_login(self.owner)
        payload = {
            "title": "Ice Cream Night",
            "description": "Pick your favorite flavor",
            "instructions": "See mom to claim",
            "household": self.household.id,
            "point_cost": 15,
            "category": "activity",
            "unlimited_quantity": "on",
            "requires_approval": "on",
            "is_active": "on",
        }
        response = self.client.post(f"{self.url}?household={self.household.id}", payload)
        self.assertEqual(response.status_code, 302)
        reward = Reward.objects.get(title="Ice Cream Night")
        self.assertIsNone(reward.quantity_available)
        self.assertIsNone(reward.quantity_remaining)

    def test_blocked_user_does_not_see_restricted_reward(self):
        blocked = User.objects.create_user(username="blocked_user", email="blocked@example.com", password="pass")
        HouseholdMembership.objects.create(
            household=self.household,
            user=blocked,
            role="member",
        )
        UserScore.objects.create(user=blocked, household=self.household, current_points=10, lifetime_points=10)

        reward = Reward.objects.create(
            household=self.household,
            title="Secret Reward",
            point_cost=5,
            category="other",
            created_by=self.owner,
            is_active=True,
        )
        reward.allowed_members.set([self.owner])

        self.client.force_login(blocked)
        response = self.client.get(reverse("home") + f"?household={self.household.id}")
        self.assertEqual(response.status_code, 200)
        available = response.context["available_rewards"]
        self.assertNotIn(reward, available)
