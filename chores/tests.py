from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from core.models import User
from core.services.chores import complete_chore_instance
from households.models import Household
from chores.models import Chore, ChoreInstance, Notification


class ChoreModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.household = Household.objects.create(name="Home", created_by=self.user)

    def test_base_points_must_be_non_negative(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Chore.objects.create(
                    household=self.household,
                    title="Test Chore",
                    category="cleaning",
                    difficulty="easy",
                    base_points=-5,
                    created_by=self.user,
                )


class ChoreCompletionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass")
        self.household = Household.objects.create(name="Home", created_by=self.user)
        self.chore = Chore.objects.create(
            household=self.household,
            title="Test Chore",
            category="cleaning",
            difficulty="easy",
            base_points=20,
            created_by=self.user,
        )
        self.instance = ChoreInstance.objects.create(
            chore=self.chore,
            assigned_to=self.user,
            due_date=timezone.now(),
        )

    def test_complete_chore_awards_points_and_creates_notification(self):
        result = complete_chore_instance(instance=self.instance, completed_by=self.user)
        self.instance.refresh_from_db()

        self.assertEqual(self.instance.status, "completed")
        self.assertEqual(self.instance.points_awarded, 20)
        self.assertEqual(result.points_result.score.current_points, 20)
        self.assertEqual(Notification.objects.count(), 1)
