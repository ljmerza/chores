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
import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_ha_config(household_id: int) -> Dict[str, Any]:
    """
    Get Home Assistant config for a household with global fallbacks.

    Tries to load from HomeAssistantConfig model first, then falls back
    to global settings.
    """
    # Import here to avoid circular imports
    from households.models import HomeAssistantConfig

    try:
        config = HomeAssistantConfig.objects.get(household_id=household_id)
        if config.is_enabled:
            return config.get_effective_config()
    except HomeAssistantConfig.DoesNotExist:
        pass

    # Fall back to global settings
    return {
        'base_url': getattr(settings, 'HA_BASE_URL', ''),
        'token': getattr(settings, 'HA_LONG_LIVED_TOKEN', ''),
        'default_target': getattr(settings, 'HA_DEFAULT_NOTIFY_TARGET', ''),
        'verify_ssl': getattr(settings, 'HA_VERIFY_SSL', True),
    }


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
    ha_base_url: Optional[str] = None
    ha_token: Optional[str] = None
    ha_default_target: Optional[str] = None
    ha_verify_ssl: Optional[bool] = None

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
        elif channel == ReminderChannel.HOME_ASSISTANT:
            target = (
                reminder.homeassistant_target
                or reminder.ha_default_target
                or getattr(settings, "HA_DEFAULT_NOTIFY_TARGET", "")
            )
            if target:
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
    Send a notification through Home Assistant's notify service.
    Requires HA_BASE_URL, HA_LONG_LIVED_TOKEN, and a notify target (per-user or default).

    Configuration priority:
    1. Per-reminder overrides (reminder.ha_* fields)
    2. Per-household config (HomeAssistantConfig model)
    3. Global settings (HA_* environment variables)
    """
    # Get base config from household or global settings
    ha_config = get_ha_config(reminder.household_id)

    # Apply per-reminder overrides
    base_url = (reminder.ha_base_url or ha_config['base_url'] or "").rstrip("/")
    token = reminder.ha_token or ha_config['token']
    default_target = reminder.ha_default_target or ha_config['default_target']

    target = reminder.homeassistant_target or default_target
    if not (base_url and token and target):
        logger.info(
            "Skipping Home Assistant notify: missing configuration (base_url/target/token). "
            "user_id=%s household_id=%s",
            reminder.user_id,
            reminder.household_id,
        )
        return

    url = f"{base_url}/api/services/notify/{target}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "message": reminder.message,
        "title": reminder.subject or "Chore reminder",
    }

    data: Dict[str, Any] = {}
    if reminder.action_link:
        data["url"] = reminder.action_link
    if reminder.due_at_iso:
        data["when"] = reminder.due_at_iso
    if data:
        payload["data"] = data

    verify_ssl = reminder.ha_verify_ssl
    if verify_ssl is None:
        verify_ssl = ha_config['verify_ssl']

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5, verify=verify_ssl)
        response.raise_for_status()
        logger.info(
            "Sent Home Assistant notify to target=%s for user_id=%s household_id=%s status=%s",
            target,
            reminder.user_id,
            reminder.household_id,
            response.status_code,
        )
    except requests.RequestException as exc:
        logger.warning(
            "Home Assistant notify failed target=%s user_id=%s household_id=%s error=%s",
            target,
            reminder.user_id,
            reminder.household_id,
            exc,
        )


def send_push(reminder: ReminderTarget) -> None:
    """
    TODO: send web push (VAPID) or HA mobile app push.
    - Requires stored push subscription per user.
    """
    raise NotImplementedError("Push reminder sending not implemented.")
