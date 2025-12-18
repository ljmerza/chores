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
    Send SMS notification via Twilio.
    - Validates user opt-in and Twilio configuration
    - Enforces 160 character limit for single-segment SMS
    - Tracks daily send limits to control costs
    """
    from django.conf import settings
    from django.core.cache import cache
    from django.utils import timezone

    # Check if Twilio is enabled
    if not getattr(settings, 'TWILIO_ENABLED', False):
        logger.debug(
            "Twilio SMS disabled in settings. user_id=%s household_id=%s",
            reminder.user_id,
            reminder.household_id,
        )
        return

    # Validate Twilio credentials
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_number = getattr(settings, 'TWILIO_FROM_NUMBER', '')

    if not (account_sid and auth_token and from_number):
        logger.warning(
            "Twilio credentials not configured. user_id=%s household_id=%s",
            reminder.user_id,
            reminder.household_id,
        )
        return

    # Validate phone number
    if not reminder.phone_e164:
        logger.debug(
            "No phone number for user. user_id=%s household_id=%s",
            reminder.user_id,
            reminder.household_id,
        )
        return

    # Check user opt-in status (requires fetching user from DB)
    try:
        from core.models import User
        user = User.objects.get(id=reminder.user_id)

        if not user.sms_notifications_enabled:
            logger.debug(
                "SMS notifications disabled for user. user_id=%s household_id=%s",
                reminder.user_id,
                reminder.household_id,
            )
            return

        if user.sms_opted_out_at:
            logger.info(
                "User opted out of SMS at %s. user_id=%s household_id=%s",
                user.sms_opted_out_at,
                reminder.user_id,
                reminder.household_id,
            )
            return
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to fetch user for SMS opt-in check. user_id=%s household_id=%s error=%s",
            reminder.user_id,
            reminder.household_id,
            exc,
        )
        return

    # Check daily send limit
    max_daily_sends = getattr(settings, 'TWILIO_MAX_DAILY_SENDS', 1000)
    cache_key = f"twilio_daily_sends_{timezone.now().date()}"
    daily_count = cache.get(cache_key, 0)

    if daily_count >= max_daily_sends:
        logger.warning(
            "Daily SMS send limit reached (%s/%s). user_id=%s household_id=%s",
            daily_count,
            max_daily_sends,
            reminder.user_id,
            reminder.household_id,
        )
        return

    # Format message with 160 character limit for single-segment SMS
    message_parts = []
    if reminder.subject:
        message_parts.append(reminder.subject)
    if reminder.message:
        message_parts.append(reminder.message)

    formatted_message = ": ".join(message_parts) if len(message_parts) > 1 else message_parts[0] if message_parts else ""

    # Add action link if available and space permits
    if reminder.action_link:
        link_text = f" {reminder.action_link}"
        if len(formatted_message) + len(link_text) <= 160:
            formatted_message += link_text
        else:
            # Truncate message to fit link
            max_message_len = 160 - len(link_text)
            formatted_message = formatted_message[:max_message_len-3] + "..." + link_text
    else:
        # Just truncate message if no link
        if len(formatted_message) > 160:
            formatted_message = formatted_message[:157] + "..."

    # Send via Twilio
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            from_=from_number,
            to=reminder.phone_e164,
            body=formatted_message,
        )

        # Increment daily send counter (expires at end of day)
        cache.set(cache_key, daily_count + 1, 86400)  # 24 hours

        logger.info(
            "SMS sent successfully. user_id=%s household_id=%s to=%s sid=%s status=%s",
            reminder.user_id,
            reminder.household_id,
            reminder.phone_e164,
            message.sid,
            message.status,
        )

    except TwilioRestException as exc:
        logger.error(
            "Twilio API error. user_id=%s household_id=%s to=%s code=%s message=%s",
            reminder.user_id,
            reminder.household_id,
            reminder.phone_e164,
            exc.code,
            exc.msg,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to send SMS. user_id=%s household_id=%s to=%s error=%s",
            reminder.user_id,
            reminder.household_id,
            reminder.phone_e164,
            exc,
        )


def send_homeassistant_notify(reminder: ReminderTarget) -> None:
    """
    Send a notification through Home Assistant's notify service.
    Requires HA_BASE_URL, HA_LONG_LIVED_TOKEN, and a notify target (per-user or default).
    """
    base_url = (reminder.ha_base_url or getattr(settings, "HA_BASE_URL", "") or "").rstrip("/")
    token = reminder.ha_token or getattr(settings, "HA_LONG_LIVED_TOKEN", "")
    default_target = reminder.ha_default_target or getattr(settings, "HA_DEFAULT_NOTIFY_TARGET", "")

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
        verify_ssl = getattr(settings, "HA_VERIFY_SSL", True)

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
    except Exception as exc:  # noqa: BLE001
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
