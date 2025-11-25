from django.db.models.signals import post_save
from django.dispatch import receiver

from households.models import HouseholdMembership, ReminderSchedule

DEFAULT_SEND_TIME = "18:00"
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _default_day_map():
    return {day: DEFAULT_SEND_TIME for day in DAY_KEYS}


@receiver(post_save, sender=HouseholdMembership)
def ensure_default_schedule_for_member(sender, instance, created, **kwargs):
    """
    Auto-create a default reminder schedule (18:00 daily) for new household members.
    Admins can edit later.
    """
    if not created:
        return

    household = instance.household
    ReminderSchedule.objects.get_or_create(
        household=household,
        user=instance.user,
        defaults={
            "per_day_time": _default_day_map(),
            "active": True,
            "created_by": getattr(household, "created_by", None),
        },
    )
