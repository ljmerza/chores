import logging

from chores.models import Notification
from core.models import User
from core.reminders import ReminderChannel, ReminderTarget, dispatch_reminder
from households.models import Household

logger = logging.getLogger(__name__)


def create_notification(
    *,
    user: User,
    household: Household,
    notification_type: str,
    title: str,
    message: str,
    link: str = "",
    deliver: bool = True,
) -> Notification:
    """
    Create a Notification record and optionally fan out to delivery channels.
    """
    notification = Notification.objects.create(
        user=user,
        household=household,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link or "",
    )
    if deliver:
        _dispatch_delivery(notification)
    return notification


def _dispatch_delivery(notification: Notification) -> None:
    """
    Send the notification over configured channels. Best-effort and non-blocking.
    """
    try:
        household = notification.household
        reminder = ReminderTarget(
            user_id=notification.user_id,
            household_id=notification.household_id,
            message=notification.message,
            subject=notification.title,
            action_link=notification.link or None,
            preferred_channels=[ReminderChannel.HOME_ASSISTANT],
            homeassistant_target=getattr(notification.user, "homeassistant_target", None),
            ha_base_url=getattr(household, "ha_base_url", None),
            ha_token=getattr(household, "ha_token", None),
            ha_default_target=getattr(household, "ha_default_target", None),
            ha_verify_ssl=getattr(household, "ha_verify_ssl", None),
        )
        dispatch_reminder(reminder)
    except (OSError, RuntimeError, AttributeError) as exc:
        logger.warning(
            "Notification delivery failed for notification_id=%s user_id=%s error=%s",
            notification.id,
            notification.user_id,
            exc,
        )
