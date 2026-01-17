"""
Shared utilities for the core application.
"""
import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_effective_timezone(household=None, recurrence_data=None):
    """
    Get timezone with documented precedence:

    1. recurrence_data.timezone (chore-specific override)
    2. household.timezone (household setting)
    3. settings.TIME_ZONE (global default)

    Args:
        household: Optional household instance with a timezone field
        recurrence_data: Optional dict that may contain a 'timezone' key

    Returns:
        ZoneInfo object for the determined timezone
    """
    tz_name = None

    # Priority 1: Recurrence-specific timezone
    if recurrence_data and recurrence_data.get('timezone'):
        tz_name = recurrence_data['timezone']

    # Priority 2: Household timezone
    elif household and getattr(household, 'timezone', None):
        tz_name = household.timezone

    # Priority 3: Global default
    else:
        tz_name = getattr(settings, 'TIME_ZONE', 'UTC')

    try:
        return ZoneInfo(tz_name)
    except (KeyError, ValueError) as exc:
        logger.warning("Invalid timezone '%s': %s. Using UTC.", tz_name, exc)
        return ZoneInfo('UTC')


def get_household_timezone(household):
    """
    Get the timezone for a household, falling back to global default.

    Args:
        household: Household instance

    Returns:
        ZoneInfo object for the household's timezone
    """
    return get_effective_timezone(household=household)


def format_datetime_local(dt, tz=None, fmt="%b %d, %I:%M %p"):
    """
    Format a datetime in a specific timezone.

    Args:
        dt: Datetime to format
        tz: ZoneInfo timezone (uses current timezone if None)
        fmt: strftime format string

    Returns:
        Formatted datetime string
    """
    if tz:
        local_dt = timezone.localtime(dt, tz)
    else:
        local_dt = timezone.localtime(dt)
    return local_dt.strftime(fmt)
