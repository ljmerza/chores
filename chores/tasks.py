import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from chores.models import Chore, ChoreInstance, Notification
from core.services.notifications import create_notification

logger = get_task_logger(__name__)


def _get_tz(tz_name: str | None):
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001
            logger.warning("Invalid timezone '%s'; falling back to default.", tz_name)
    return timezone.get_current_timezone()


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
    Generate upcoming instances for recurring chores within a lookahead window.
    Uses `recurrence_pattern` + `recurrence_data` (see docs/CHORE_DUE_RULES.md).
    """
    now = timezone.now()
    lookahead_days = getattr(settings, "RECURRENCE_LOOKAHEAD_DAYS", 30)
    horizon = now + timedelta(days=lookahead_days)

    recurring = Chore.objects.filter(
        recurrence_pattern__in=["daily", "weekly", "biweekly", "monthly", "custom"],
    ).select_related("assigned_to")

    for chore in recurring:
        due_dates = _compute_due_dates(chore, now, horizon)
        if not due_dates:
            continue

        for due_dt in due_dates:
            defaults = {
                "assigned_to": chore.assigned_to,
                "status": "available",
            }

            with transaction.atomic():
                _, created = ChoreInstance.objects.get_or_create(
                    chore=chore,
                    due_date=due_dt,
                    defaults=defaults,
                )
                if created:
                    logger.info(
                        "Created recurring instance chore_id=%s due=%s",
                        chore.id,
                        due_dt.isoformat(),
                    )


def _compute_due_dates(chore: Chore, now, horizon):
    """
    Determine which due dates to materialize for a chore within the window.
    """
    data = chore.recurrence_data or {}
    start_date = _determine_start_date(chore, data)
    if not start_date:
        return []

    end_date = _parse_date(data.get("end_date"))
    if end_date and end_date < start_date:
        return []

    max_occurrences = data.get("max_occurrences")
    try:
        max_occurrences = int(max_occurrences) if max_occurrences is not None else None
    except Exception:  # noqa: BLE001
        max_occurrences = None
    base_dates = _generate_candidate_dates(
        chore=chore,
        start_date=start_date,
        end_date=end_date,
        window_start=max(start_date, now.date()),
        window_end=horizon.date(),
        recurrence_data=data,
    )

    include_dates = {
        d
        for d in (_parse_date(v) for v in (data.get("filters", {}) or {}).get("include_dates", []) or [])
        if d and (start_date <= d <= horizon.date())
    }

    all_dates = list(base_dates | include_dates)
    all_dates.sort()
    if max_occurrences:
        all_dates = all_dates[:max_occurrences]

    due_time = _determine_due_time(chore, data)
    tz = _get_tz(data.get("timezone"))

    results = []
    for d in all_dates:
        if end_date and d > end_date:
            break
        dt = datetime.combine(d, due_time)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, tz)
        if now <= dt <= horizon:
            results.append(dt)
    return results


def _determine_start_date(chore: Chore, data: dict) -> date | None:
    start_date = _parse_date(data.get("start_date"))
    if start_date:
        return start_date
    if chore.due_date:
        return timezone.localdate(chore.due_date)
    try:
        return timezone.localdate()
    except Exception:  # noqa: BLE001
        return None


def _determine_due_time(chore: Chore, data: dict) -> time:
    due_time = data.get("due_time")
    if isinstance(due_time, str):
        try:
            hours, minutes = [int(x) for x in due_time.split(":", 1)]
            return time(hour=hours, minute=minutes)
        except Exception:  # noqa: BLE001
            logger.warning("Invalid due_time '%s'; falling back to chore.due_date time/default.", due_time)
    if chore.due_date:
        return timezone.localtime(chore.due_date).timetz()
    return time(hour=17, minute=0)


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(value)
    except Exception:  # noqa: BLE001
        return None


def _generate_candidate_dates(
    *,
    chore: Chore,
    start_date: date,
    end_date: date | None,
    window_start: date,
    window_end: date,
    recurrence_data: dict,
) -> set[date]:
    """
    Iterate day-by-day within the window and pick dates that satisfy the rule and filters.
    """
    allowed_months = set((recurrence_data.get("filters", {}) or {}).get("allowed_months", []) or [])
    try:
        allowed_months = {int(m) for m in allowed_months}
    except Exception:  # noqa: BLE001
        allowed_months = set()
    exclude_dates = {
        d for d in (_parse_date(v) for v in (recurrence_data.get("filters", {}) or {}).get("exclude_dates", []) or []) if d
    }

    rule = recurrence_data.get("rule") or {}
    pattern = chore.recurrence_pattern

    matches: set[date] = set()
    current = window_start
    while current <= window_end:
        if end_date and current > end_date:
            break
        if allowed_months and current.month not in allowed_months:
            current += timedelta(days=1)
            continue
        if current in exclude_dates:
            current += timedelta(days=1)
            continue
        if _matches_pattern(current, start_date, pattern, rule):
            matches.add(current)
        current += timedelta(days=1)
    return matches


def _matches_pattern(current: date, anchor: date, pattern: str, rule: dict) -> bool:
    if pattern == "daily":
        every = rule.get("every") or rule.get("interval_days") or 1
        delta_days = (current - anchor).days
        return delta_days >= 0 and delta_days % max(every, 1) == 0

    if pattern in ["weekly", "biweekly"]:
        days_of_week = rule.get("days_of_week") or [anchor.weekday()]
        interval_weeks = rule.get("interval_weeks") or (2 if pattern == "biweekly" else 1)
        weeks_since_start = (current - anchor).days // 7
        return weeks_since_start >= 0 and weeks_since_start % max(interval_weeks, 1) == 0 and current.weekday() in days_of_week

    if pattern == "monthly":
        mode = rule.get("mode")
        if mode == "nth_weekday":
            nth = rule.get("nth", 1)
            weekday = rule.get("weekday", anchor.weekday())
            return _is_nth_weekday(current, weekday, nth)
        day_of_month = rule.get("day_of_month", anchor.day)
        roll_strategy = rule.get("roll_strategy", "last_day")
        last_day = calendar.monthrange(current.year, current.month)[1]
        expected_day = last_day if (day_of_month > last_day and roll_strategy == "last_day") else day_of_month
        return current.day == expected_day

    if pattern == "custom":
        specific_days = rule.get("specific_days_of_month")
        if specific_days:
            return current.day in specific_days
        custom_dates = {d for d in (_parse_date(v) for v in rule.get("custom_dates", []) or []) if d}
        return current in custom_dates

    return False


def _is_nth_weekday(current: date, weekday: int, nth: int) -> bool:
    if current.weekday() != weekday:
        return False
    if nth == -1:
        last_day = calendar.monthrange(current.year, current.month)[1]
        return current.day + 7 > last_day
    count = 0
    day = 1
    last_day = calendar.monthrange(current.year, current.month)[1]
    while day <= last_day:
        dt = date(current.year, current.month, day)
        if dt.weekday() == weekday:
            count += 1
            if dt == current:
                return count == nth
        day += 1
    return False
