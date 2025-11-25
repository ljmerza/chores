import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from chores.models import Chore, ChoreInstance, Notification
from core.services.notifications import create_notification
from households.models import Leaderboard, PointTransaction, UserScore
from households.models import ReminderSchedule

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


def _scheduled_users_by_household():
    """
    Return a mapping of household_id -> set(user_id) for members with an active schedule.
    """
    scheduled: dict[int, set[int]] = {}
    qs = ReminderSchedule.objects.filter(active=True).values_list("household_id", "user_id")
    for household_id, user_id in qs:
        scheduled.setdefault(household_id, set()).add(user_id)
    return scheduled


def _is_user_scheduled(user_id: int, household_id: int, scheduled_users: dict[int, set[int]]) -> bool:
    return user_id in scheduled_users.get(household_id, set())


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        hour, minute = [int(x) for x in value.split(":", 1)]
        return time(hour=hour, minute=minute)
    except Exception:  # noqa: BLE001
        logger.warning("Invalid schedule time '%s'; skipping.", value)
        return None


def _collect_due_items(user, household, window_end, now, tz):
    """
    Return counts and earliest due time for chores assigned to the user within the window.
    """
    active_statuses = ["available", "claimed", "in_progress"]
    earliest_due = None
    overdue_count = 0
    total = 0

    instances = (
        ChoreInstance.objects.filter(
            chore__household=household,
            status__in=active_statuses,
            due_date__lte=window_end,
        )
        .filter(Q(assigned_to=user) | Q(claimed_by=user))
        .only("due_date")
    )
    chores = (
        Chore.objects.filter(
            household=household,
            assigned_to=user,
            status__in=["pending", "in_progress"],
            due_date__isnull=False,
            due_date__lte=window_end,
        ).only("due_date")
    )

    def _bump(dt):
        nonlocal earliest_due, overdue_count, total
        total += 1
        if dt <= now:
            overdue_count += 1
        if earliest_due is None or dt < earliest_due:
            earliest_due = dt

    for inst in instances:
        _bump(inst.due_date)
    for chore in chores:
        _bump(chore.due_date)

    return {
        "count": total,
        "overdue": overdue_count,
        "earliest_due": _format_due_local(earliest_due, tz) if earliest_due else None,
    }


def _format_due_local(dt, tz):
    return timezone.localtime(dt, tz).strftime("%b %d, %I:%M %p")


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

    scheduled_users = _scheduled_users_by_household()

    _scan_instances(now, lead_window, cooldown_minutes, scheduled_users)
    _scan_base_chores(now, lead_window, cooldown_minutes, scheduled_users)


def _scan_instances(now, lead_window, cooldown_minutes, scheduled_users):
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

        # Users with an active schedule get their reminders via the scheduled digest task.
        if _is_user_scheduled(user.id, instance.chore.household_id, scheduled_users):
            if due_state == "overdue" and instance.status in active_statuses:
                instance.status = "expired"
                instance.save(update_fields=["status"])
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


def _scan_base_chores(now, lead_window, cooldown_minutes, scheduled_users):
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

        if _is_user_scheduled(user.id, chore.household_id, scheduled_users):
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
def send_scheduled_chore_digests():
    """
    Send due/overdue reminders based on per-user schedules (one time per day).
    Runs frequently and fires when the current local time is within a tolerance window.
    """
    now = timezone.now()
    lead_minutes = getattr(settings, "REMINDER_LEAD_TIME_MINUTES", 60)
    cooldown_minutes = getattr(settings, "REMINDER_COOLDOWN_MINUTES", 120)
    interval_minutes = getattr(settings, "REMINDER_SCHEDULE_DIGEST_INTERVAL_MINUTES", 5)
    tolerance_minutes = max(1, interval_minutes // 2 or 1)

    schedules = ReminderSchedule.objects.filter(active=True).select_related("household", "user")
    for schedule in schedules:
        household = schedule.household
        user = schedule.user
        tz = _get_tz(getattr(household, "timezone", None))
        local_now = now.astimezone(tz)
        day_key = local_now.strftime("%a").lower()[:3]
        per_day = schedule.per_day_time or {}
        send_time_str = per_day.get(day_key)
        send_time = _parse_hhmm(send_time_str)
        if not send_time:
            continue

        scheduled_local = local_now.replace(
            hour=send_time.hour,
            minute=send_time.minute,
            second=0,
            microsecond=0,
        )

        delta_seconds = abs((local_now - scheduled_local).total_seconds())
        if delta_seconds > tolerance_minutes * 60:
            continue

        window_end_local = scheduled_local + timedelta(minutes=lead_minutes)
        window_end = window_end_local.astimezone(timezone.utc)

        due_summary = _collect_due_items(user, household, window_end, now, tz)
        if due_summary["count"] == 0:
            continue

        link_key = f"digest-{scheduled_local.date()}-{scheduled_local.strftime('%H%M')}"
        if _recent_notification("chore_due", user.id, household.id, link_key, cooldown_minutes):
            continue

        overdue_note = f" ({due_summary['overdue']} overdue)" if due_summary["overdue"] else ""
        next_due_note = f" Next due {due_summary['earliest_due']}." if due_summary["earliest_due"] else ""
        message = f"You have {due_summary['count']} chore(s) due or overdue{overdue_note}.{next_due_note}"

        create_notification(
            user=user,
            household=household,
            notification_type="chore_due",
            title="Chore reminder",
            message=message.strip(),
            link=f"/chores?digest={link_key}",
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


@shared_task
def recompute_streaks_and_leaderboards():
    """
    Recalculate streaks/totals and leaderboard standings from recent activity.
    """
    now = timezone.now()
    _recompute_streaks(now)
    _recompute_leaderboards(now)
    _prune_old_data()


def _recompute_streaks(now):
    """
    Rebuild streaks per user/household based on completed/verified instances.
    """
    completions = (
        ChoreInstance.objects.filter(
            status__in=["completed", "verified"],
            completed_at__isnull=False,
        )
        .select_related("chore", "assigned_to", "claimed_by")
        .order_by()
    )

    stats = {}
    for instance in completions:
        user_id = instance.claimed_by_id or instance.assigned_to_id
        if not user_id:
            continue
        key = (instance.chore.household_id, user_id)
        payload = stats.setdefault(key, {"datetimes": []})
        payload["datetimes"].append(instance.completed_at)

    for (household_id, user_id), payload in stats.items():
        datetimes = payload["datetimes"]
        if not datetimes:
            continue

        dates_desc = sorted({timezone.localdate(dt) for dt in datetimes}, reverse=True)
        current_streak = _calc_current_streak(dates_desc)
        longest_streak = _calc_longest_streak(dates_desc)
        last_completed = max(datetimes)
        total_completed = len(datetimes)

        with transaction.atomic():
            score, _ = UserScore.objects.select_for_update().get_or_create(
                user_id=user_id,
                household_id=household_id,
                defaults={
                    "current_points": 0,
                    "lifetime_points": 0,
                    "total_chores_completed": 0,
                },
            )
            score.current_streak = current_streak
            score.longest_streak = max(longest_streak, score.longest_streak)
            score.total_chores_completed = total_completed
            score.last_chore_completed_at = last_completed
            score.save(
                update_fields=[
                    "current_streak",
                    "longest_streak",
                    "total_chores_completed",
                    "last_chore_completed_at",
                    "updated_at",
                ]
            )


def _calc_current_streak(dates_desc: list[date]) -> int:
    if not dates_desc:
        return 0
    streak = 1
    for idx in range(1, len(dates_desc)):
        delta = (dates_desc[idx - 1] - dates_desc[idx]).days
        if delta == 1:
            streak += 1
        elif delta == 0:
            continue
        else:
            break
    return streak


def _calc_longest_streak(dates_desc: list[date]) -> int:
    if not dates_desc:
        return 0
    longest = 1
    run = 1
    for idx in range(1, len(dates_desc)):
        delta = (dates_desc[idx - 1] - dates_desc[idx]).days
        if delta == 1:
            run += 1
        elif delta == 0:
            continue
        else:
            run = 1
        if run > longest:
            longest = run
    return longest


def _recompute_leaderboards(now):
    """
    Rebuild leaderboard rows for daily/weekly/monthly/all_time.
    """
    periods = _leaderboard_periods(now)
    for period, start_date, end_date in periods:
        entries = _aggregate_leaderboard(period, start_date, end_date)
        _upsert_leaderboard(period, start_date, end_date, entries)


def _leaderboard_periods(now):
    today = timezone.localdate(now)
    start_week = today - timedelta(days=today.weekday())  # Monday start
    start_month = today.replace(day=1)
    last_day_month = calendar.monthrange(today.year, today.month)[1]
    end_month = today.replace(day=last_day_month)

    return [
        ("daily", today, today),
        ("weekly", start_week, start_week + timedelta(days=6)),
        ("monthly", start_month, end_month),
        ("all_time", date(1970, 1, 1), None),
    ]


def _aggregate_leaderboard(period, start_date: date, end_date: date | None):
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min))
    qs = PointTransaction.objects.filter(created_at__gte=start_dt)
    if end_date:
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max))
        qs = qs.filter(created_at__lte=end_dt)

    aggregates = qs.values("household_id", "user_id").annotate(
        points=Sum("amount"),
        chores_completed=Count("id", filter=Q(transaction_type="earned")),
    )

    by_household = {}
    for row in aggregates:
        household_id = row["household_id"]
        by_household.setdefault(household_id, []).append(row)
    return by_household


def _upsert_leaderboard(period, start_date: date, end_date: date | None, entries_by_household):
    for household_id, entries in entries_by_household.items():
        entries.sort(key=lambda r: (-r["points"], -r["chores_completed"], r["user_id"]))
        user_ids = []
        for idx, row in enumerate(entries, start=1):
            user_ids.append(row["user_id"])
            Leaderboard.objects.update_or_create(
                household_id=household_id,
                user_id=row["user_id"],
                period=period,
                period_start_date=start_date,
                defaults={
                    "period_end_date": end_date,
                    "points": row["points"] or 0,
                    "chores_completed": row["chores_completed"] or 0,
                    "rank": idx,
                },
            )

        Leaderboard.objects.filter(
            household_id=household_id,
            period=period,
            period_start_date=start_date,
        ).exclude(user_id__in=user_ids).delete()


def _prune_old_data():
    """
    Remove stale notifications and completed/expired instances per retention settings.
    """
    notif_days = getattr(settings, "NOTIFICATION_RETENTION_DAYS", 90)
    instance_days = getattr(settings, "COMPLETED_INSTANCE_RETENTION_DAYS", 180)
    now = timezone.now()

    if notif_days > 0:
        cutoff = now - timedelta(days=notif_days)
        deleted, _ = Notification.objects.filter(created_at__lt=cutoff).delete()
        if deleted:
            logger.info("Pruned %s old notifications (>%s days)", deleted, notif_days)

    if instance_days > 0:
        cutoff = now - timedelta(days=instance_days)
        deleted, _ = (
            ChoreInstance.objects.filter(
                status__in=["completed", "verified", "expired"],
                completed_at__lt=cutoff,
            ).delete()
        )
        if deleted:
            logger.info("Pruned %s old chore instances (>%s days)", deleted, instance_days)
