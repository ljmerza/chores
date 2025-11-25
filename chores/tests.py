from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import User
from core.services.chores import complete_chore_instance
from households.models import Household
from chores import tasks
from chores.models import Chore, ChoreInstance, Notification, MAX_CHORE_POINTS


class ChoreModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
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

    def test_base_points_clean_validates_range(self):
        chore = Chore(
            household=self.household,
            title="Validate Points",
            category="cleaning",
            difficulty="easy",
            base_points=0,
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            chore.full_clean()

        chore.base_points = MAX_CHORE_POINTS + 1
        with self.assertRaises(ValidationError):
            chore.full_clean()


class ChoreCompletionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
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


class CeleryTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", email="owner@example.com", password="pass")
        self.household = Household.objects.create(name="Home", created_by=self.user)

    @override_settings(RECURRENCE_LOOKAHEAD_DAYS=30)
    def test_generate_recurring_instances_creates_from_rule(self):
        now = timezone.now()
        start_date = timezone.localdate(now)
        due_time = (timezone.localtime(now + timedelta(hours=1))).strftime("%H:%M")

        chore = Chore.objects.create(
            household=self.household,
            title="Weekly trash",
            category="cleaning",
            difficulty="easy",
            base_points=5,
            created_by=self.user,
            recurrence_pattern="weekly",
            recurrence_data={
                "start_date": start_date.isoformat(),
                "due_time": due_time,
                "rule": {"days_of_week": [start_date.weekday()]},
            },
        )

        tasks.generate_recurring_instances()

        instances = chore.instances.all()
        self.assertEqual(instances.count(), 1)
        instance = instances.first()
        self.assertEqual(instance.assigned_to, None)
        self.assertEqual(instance.status, "available")
        self.assertEqual(timezone.localdate(instance.due_date), start_date)

        # Idempotent run should not create duplicates
        tasks.generate_recurring_instances()
        self.assertEqual(chore.instances.count(), 1)

    @override_settings(REMINDER_LEAD_TIME_MINUTES=120, REMINDER_COOLDOWN_MINUTES=120)
    def test_scan_due_items_sends_due_and_overdue_notifications(self):
        now = timezone.now()
        chore = Chore.objects.create(
            household=self.household,
            title="Laundry",
            category="cleaning",
            difficulty="easy",
            base_points=5,
            created_by=self.user,
            assigned_to=self.user,
            due_date=now + timedelta(minutes=30),
        )

        instance = ChoreInstance.objects.create(
            chore=chore,
            assigned_to=self.user,
            due_date=now - timedelta(minutes=30),
            status="available",
        )

        tasks.scan_due_items()

        notifications = Notification.objects.order_by("created_at")
        self.assertEqual(notifications.count(), 2)
        types = {n.notification_type for n in notifications}
        self.assertIn("chore_due", types)
        self.assertIn("chore_overdue", types)

        instance.refresh_from_db()
        self.assertEqual(instance.status, "expired")
