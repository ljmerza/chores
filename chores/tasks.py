from datetime import timedelta

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from chores.models import Chore, ChoreInstance, Notification
from core.services.notifications import create_notification

logger = get_task_logger(__name__)


def _format_due(dt):
    return timezone.localtime(dt).strftime("%b %d, %I:%M %p")


def _recent_notification(notification_type: str, user_id: int, household_id: int, link_key: str, cooldown_minutes: int) -> bool:
    """
    Avoid spamming users with duplicate reminders within a cooldown window.
    """
    cutoff = timezone.now() - timedelta(minutes=cooldown_minutes)
    filters = {
        "user_id": user_id,
        "household_id": household_id,
        "notification_type": notification_type,
        "created_at__gte": cutoff,
    }
    if link_key:
        filters["link__icontains"] = link_key
    return Notification.objects.filter(**filters).exists()


@shared_task
def scan_due_items():
    """
    Scan for chores and chore instances that are due soon or overdue.
    - Sends a notification (once per cooldown window).
    - Marks instances as expired when overdue.
    """
    now = timezone.now()
    lead_minutes = getattr(settings, "REMINDER_LEAD_TIME_MINUTES", 60)
    cooldown_minutes = getattr(settings, "REMINDER_COOLDOWN_MINUTES", 120)
    lead_window = now + timedelta(minutes=lead_minutes)

    _scan_instances(now, lead_window, cooldown_minutes)
    _scan_base_chores(now, lead_window, cooldown_minutes)


def _scan_instances(now, lead_window, cooldown_minutes):
    active_statuses = ["available", "claimed", "in_progress"]
    instances = (
        ChoreInstance.objects.filter(
            status__in=active_statuses,
            due_date__lte=lead_window,
        )
        .select_related("chore", "assigned_to", "claimed_by", "chore__household")
        .order_by("due_date")
    )

    for instance in instances:
        due_state = "overdue" if instance.due_date <= now else "due"
        user = instance.assigned_user
        if not user:
            continue

        notif_type = "chore_overdue" if due_state == "overdue" else "chore_due"
        link_key = f"chore-instance-{instance.id}"
        if _recent_notification(notif_type, user.id, instance.chore.household_id, link_key, cooldown_minutes):
            continue

        message = f"'{instance.chore.title}' is {due_state} (due {_format_due(instance.due_date)})."
        create_notification(
            user=user,
            household=instance.chore.household,
            notification_type=notif_type,
            title="Chore overdue" if due_state == "overdue" else "Chore due soon",
            message=message,
            link=f"/chores/{instance.chore_id}/instances/{instance.id}",
        )

        if due_state == "overdue" and instance.status in active_statuses:
            instance.status = "expired"
            instance.save(update_fields=["status"])


def _scan_base_chores(now, lead_window, cooldown_minutes):
    """
    Cover non-instance chores so existing flows still get reminders.
    """
    chores = (
        Chore.objects.filter(
            status__in=["pending", "in_progress"],
            due_date__isnull=False,
            due_date__lte=lead_window,
        )
        .select_related("assigned_to", "household")
        .order_by("due_date")
    )

    for chore in chores:
        user = chore.assigned_to
        if not user:
            continue

        due_state = "overdue" if chore.due_date <= now else "due"
        notif_type = "chore_overdue" if due_state == "overdue" else "chore_due"
        link_key = f"chore-{chore.id}"

        if _recent_notification(notif_type, user.id, chore.household_id, link_key, cooldown_minutes):
            continue

        message = f"'{chore.title}' is {due_state} (due {_format_due(chore.due_date)})."
        create_notification(
            user=user,
            household=chore.household,
            notification_type=notif_type,
            title="Chore overdue" if due_state == "overdue" else "Chore due soon",
            message=message,
            link=f"/chores/{chore.id}",
        )


@shared_task
def generate_recurring_instances():
    """
    Minimal recurrence placeholder:
    - Ensures each recurring chore has at least one upcoming instance.
    - Avoids duplicate instances for the same due_date.
    """
    now = timezone.now()
    lookahead_days = getattr(settings, "RECURRENCE_LOOKAHEAD_DAYS", 30)
    horizon = now + timedelta(days=lookahead_days)

    recurring = Chore.objects.filter(
        recurrence_pattern__in=["daily", "weekly", "biweekly", "monthly", "custom"],
        due_date__isnull=False,
    ).select_related("assigned_to")

    for chore in recurring:
        existing = chore.instances.filter(due_date__gte=now, due_date__lte=horizon).exists()
        if existing:
            continue

        defaults = {
            "assigned_to": chore.assigned_to,
            "due_date": chore.due_date,
            "status": "available",
        }

        with transaction.atomic():
            ChoreInstance.objects.get_or_create(
                chore=chore,
                due_date=chore.due_date,
                defaults=defaults,
            )
            logger.info("Created placeholder instance for recurring chore %s due %s", chore.id, chore.due_date)
