"""
Stubbed reminder dispatch layer for multi-channel notifications.

Intended channels:
- email: Django email backend
- sms: provider integration (e.g., Twilio)
- homeassistant: call Home Assistant notify service (requires setup)
- push: web/push notifications (PWA or HA mobile app)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ReminderChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    HOME_ASSISTANT = "homeassistant"
    PUSH = "push"


@dataclass
class ReminderTarget:
    user_id: int
    household_id: int
    message: str
    subject: Optional[str] = None
    action_link: Optional[str] = None
    due_at_iso: Optional[str] = None
    preferred_channels: List[ReminderChannel] = field(default_factory=list)

    # Contact endpoints (fill as available)
    email: Optional[str] = None
    phone_e164: Optional[str] = None
    homeassistant_target: Optional[str] = None  # e.g., notify.mobile_app_x
    push_subscription: Optional[Dict[str, Any]] = None  # web push payload

    # Control knobs
    cooldown_minutes: int = 60
    quiet_hours: Optional[Dict[str, int]] = None  # {"start": 22, "end": 7} 24h clock


def dispatch_reminder(reminder: ReminderTarget) -> None:
    """
    Placeholder dispatcher; wire Celery tasks to call channel-specific senders.
    """
    for channel in _resolve_channels(reminder):
        send_via_channel(reminder, channel)


def _resolve_channels(reminder: ReminderTarget) -> List[ReminderChannel]:
    """
    Determine which channels to try based on preferences and available contact info.
    """
    if reminder.preferred_channels:
        candidates = reminder.preferred_channels
    else:
        candidates = [
            ReminderChannel.EMAIL,
            ReminderChannel.SMS,
            ReminderChannel.HOME_ASSISTANT,
            ReminderChannel.PUSH,
        ]

    available: List[ReminderChannel] = []
    for channel in candidates:
        if channel == ReminderChannel.EMAIL and reminder.email:
            available.append(channel)
        elif channel == ReminderChannel.SMS and reminder.phone_e164:
            available.append(channel)
        elif channel == ReminderChannel.HOME_ASSISTANT and reminder.homeassistant_target:
            available.append(channel)
        elif channel == ReminderChannel.PUSH and reminder.push_subscription:
            available.append(channel)
    return available


def send_via_channel(reminder: ReminderTarget, channel: ReminderChannel) -> None:
    """
    Channel-specific stubs. Replace with real integrations.
    """
    if channel == ReminderChannel.EMAIL:
        send_email(reminder)
    elif channel == ReminderChannel.SMS:
        send_sms(reminder)
    elif channel == ReminderChannel.HOME_ASSISTANT:
        send_homeassistant_notify(reminder)
    elif channel == ReminderChannel.PUSH:
        send_push(reminder)


def send_email(reminder: ReminderTarget) -> None:
    """
    TODO: implement with Django email backend.
    - Use subject/message; include action_link.
    - Respect quiet hours/cooldown externally (task layer).
    """
    raise NotImplementedError("Email reminder sending not implemented.")


def send_sms(reminder: ReminderTarget) -> None:
    """
    TODO: integrate SMS provider (e.g., Twilio).
    - Guard against long messages; include short action_link.
    """
    raise NotImplementedError("SMS reminder sending not implemented.")


def send_homeassistant_notify(reminder: ReminderTarget) -> None:
    """
    TODO: POST to Home Assistant /api/services/notify/<target>
    - Requires base URL and long-lived token in settings/env.
    """
    raise NotImplementedError("Home Assistant notify sending not implemented.")


def send_push(reminder: ReminderTarget) -> None:
    """
    TODO: send web push (VAPID) or HA mobile app push.
    - Requires stored push subscription per user.
    """
    raise NotImplementedError("Push reminder sending not implemented.")
