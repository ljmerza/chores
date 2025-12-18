# Reminder System Stubs & Channel Notes

Goal: multi-channel reminders (email, SMS, Home Assistant notify, push) with Celery-driven scheduling. This doc describes how to wire it up; code is in `core/reminders.py`.

## Channels Implementation Status
- **Email**: Stubbed - Django email backend; template includes subject/body/action link. (TODO)
- **SMS**: ✅ **Implemented** - Twilio integration with opt-in/opt-out support, E.164 validation, daily send limits, and STOP/START webhook handling.
- **Home Assistant notify**: ✅ **Implemented** - POST to `/api/services/notify/<target>` with long-lived token.
- **Push**: Stubbed - web push (VAPID) or Home Assistant mobile app push; requires stored subscription. (TODO)

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
- `HA_BASE_URL`, `HA_LONG_LIVED_TOKEN`, default `HA_NOTIFY_TARGET`, `HA_VERIFY_SSL`
- **SMS (Twilio):**
  - `TWILIO_ENABLED` (boolean, default False)
  - `TWILIO_ACCOUNT_SID` (from Twilio console)
  - `TWILIO_AUTH_TOKEN` (from Twilio console)
  - `TWILIO_FROM_NUMBER` (E.164 format, e.g., +15551234567)
  - `TWILIO_MAX_DAILY_SENDS` (integer, default 1000)
- `PUSH_VAPID_PUBLIC_KEY`, `PUSH_VAPID_PRIVATE_KEY` (TODO)

## SMS Implementation Details (Twilio)

### User Model Fields
- `phone_number` (CharField, max 20, nullable, unique) - E.164 format phone number
- `sms_notifications_enabled` (BooleanField, default False) - User opt-in status
- `sms_opted_out_at` (DateTimeField, nullable) - Timestamp of last opt-out via STOP keyword

### Features Implemented
1. **Message Sending** (`core/reminders.py:send_sms()`):
   - Validates Twilio credentials and opt-in status
   - Enforces 160-character limit for single-segment SMS
   - Truncates messages intelligently to fit action links
   - Tracks daily send count via Django cache to enforce limits
   - Logs all sends with user_id, household_id, and Twilio SID

2. **Opt-Out/Opt-In Webhook** (`/webhooks/twilio/sms/`):
   - Validates Twilio signature to prevent spoofing
   - Handles STOP keywords: STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT
   - Handles START keywords: START, SUBSCRIBE, YES, UNSTOP
   - Updates user model and responds with TwiML confirmation
   - Logs all opt-in/opt-out events

3. **Admin UI** (Admin Hub > Manage Notifications):
   - Per-user phone number configuration (E.164 validation)
   - Per-user SMS opt-in checkbox
   - Form validation ensures phone numbers match E.164 pattern
   - Bulk update support for household members

### Cost Controls
- Daily send limit enforced via Redis/Django cache
- Per-user cooldown respects `REMINDER_COOLDOWN_MINUTES`
- Opt-in required - disabled by default
- Admins can monitor Twilio usage via Twilio console

### Security
- Twilio webhook signature validation prevents unauthorized requests
- Phone numbers stored with model-level E.164 validation
- Auth token stored in environment variables (never committed)
- CSRF exemption for webhook endpoint (Twilio doesn't support CSRF tokens)

## Implementation Checklist
- ✅ Add Celery + beat and a task to find due/overdue `ChoreInstance` rows.
- ✅ Add per-user contact/preference model (extended `User` profile) and admin forms.
- ✅ **SMS**: Implement Twilio sender in `core/reminders.py:send_sms()`; handle exceptions and retries.
- ✅ **SMS**: Add webhook for STOP/START keyword handling at `/webhooks/twilio/sms/`.
- ✅ **SMS**: Add phone number and SMS opt-in fields to Admin UI.
- ✅ **Home Assistant**: Implement HA notify sender in `core/reminders.py:send_homeassistant_notify()`.
- ⏳ **Email**: Implement email sender using Django email backend (TODO).
- ⏳ **Push**: Implement web push (VAPID) or HA mobile app push (TODO).
- ✅ Add cooldown/quiet-hour enforcement in the task layer before dispatch.
- ⏳ Add minimal tests covering channel selection, cooldown logic, and SMS/HA payload shape (TODO).
