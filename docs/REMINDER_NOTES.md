# Reminder System Stubs & Channel Notes

Goal: multi-channel reminders (email, SMS, Home Assistant notify, push) with Celery-driven scheduling. This doc describes how to wire it up; code is stubbed in `core/reminders.py`.

## Channels to Support
- Email: Django email backend; template includes subject/body/action link.
- SMS: provider integration (e.g., Twilio, SNS); short message with optional shortened link.
- Home Assistant notify: POST to `/api/services/notify/<target>` with long-lived token.
- Push: web push (VAPID) or Home Assistant mobile app push; requires stored subscription.

## Data Needed
- Per-user contact fields: `email`, `phone_e164`, `homeassistant_target`, `push_subscription`.
- Preferences: channel priority list, quiet hours, per-household opt-in/out.
- Cooldown tracking: prevent duplicate reminders within N minutes per (user, chore_instance, type).
- Home Assistant: per-household `ha_base_url`, `ha_token`, `ha_default_target` (set via Admin Hub > Notifications) and per-user `homeassistant_target`; optional env vars remain as fallbacks only.

## Task Flow (Celery, stub)
1) Beat schedules `reminders.scan_due_instances` every 5–15 minutes.
2) For each due/overdue instance (status available/claimed/in_progress), build `ReminderTarget`.
3) Call `core.reminders.dispatch_reminder(target)`; channel fan-out occurs there.
4) Persist a `Notification` row for in-app display regardless of external channel success.

## Configuration Knobs (env/settings)
- `REMINDER_LEAD_TIME_MINUTES` (e.g., 60)
- `REMINDER_COOLDOWN_MINUTES` (e.g., 120)
- `REMINDER_QUIET_HOURS_START`, `REMINDER_QUIET_HOURS_END` (optional)
- `HA_BASE_URL`, `HA_LONG_LIVED_TOKEN`, default `HA_NOTIFY_TARGET`
- `SMS_PROVIDER`, `SMS_FROM_NUMBER`
- `PUSH_VAPID_PUBLIC_KEY`, `PUSH_VAPID_PRIVATE_KEY`

## Implementation Checklist
- Add Celery + beat and a task to find due/overdue `ChoreInstance` rows.
- Add per-user contact/preference model (or extend `User` profile) and admin forms.
- Implement channel senders in `core/reminders.py`; handle exceptions and retries.
- Add cooldown/quiet-hour enforcement in the task layer before dispatch.
- Add minimal tests covering channel selection, cooldown logic, and HA payload shape.
