from typing import Optional

from chores.models import Notification
from core.models import User
from households.models import Household


def create_notification(
    *,
    user: User,
    household: Household,
    notification_type: str,
    title: str,
    message: str,
    link: str = "",
) -> Notification:
    """
    Create a Notification record. Channel delivery (email/push/etc.) is handled elsewhere.
    """
    return Notification.objects.create(
        user=user,
        household=household,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link or "",
    )
