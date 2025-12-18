# Twilio SMS Notification Integration Plan

Plan for integrating Twilio to send SMS notifications for chore reminders, rewards approvals, and other household alerts. Focus on reliable delivery, cost control, message formatting, and privacy-conscious phone number handling.

## Goals & Scope
- Implement `send_sms()` in `core/reminders.py` using Twilio's API for SMS delivery.
- Store phone numbers securely per user (E.164 format); admin-controlled for child accounts.
- Respect SMS character limits, message costs, and opt-out requirements (TCPA compliance).
- Phase 1: chore due/overdue reminders and reward status updates; exclude one-time verification codes or complex multi-message flows.
- Phase 2 (optional): MMS support for photo attachments, two-way SMS interactions, delivery status webhooks.

## Assumptions & Decisions to Lock
- Phone number storage: add `User.phone_number` (CharField, E.164 format, optional, unique); admins can edit for household members.
- Twilio account: single account per deployment; credentials in settings (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`).
- Message length: enforce 160 chars for single-segment SMS; truncate or reject if over limit; include short action links only.
- Opt-in/opt-out: users enable SMS via profile setting (`User.sms_notifications_enabled`, default False); provide opt-out keyword handling (e.g., "STOP").
- International support: allow international E.164 numbers; document Twilio international pricing and enable geo-permissions as needed.
- Rate limiting: apply per-user cooldown (`REMINDER_COOLDOWN_MINUTES`) and global SMS send limits to avoid bill shock.

## Data Model Changes
- `User.phone_number` (CharField, max_length=20, blank=True, null=True, unique=True):
  - Store E.164 format (e.g., +12025551234).
  - Validation in model/form to enforce E.164 pattern.
- `User.sms_notifications_enabled` (BooleanField, default=False):
  - Users must opt-in; admins can toggle for child accounts.
  - Checked before dispatching SMS in `send_sms()`.
- `User.sms_opted_out_at` (DateTimeField, blank=True, null=True):
  - Timestamp when user opted out via "STOP" keyword.
  - If set, block all SMS sends; require explicit opt-in to clear.
- Optional: `SMSLog` model for audit trail (user, message, status, cost, sent_at, twilio_sid) if detailed tracking is required beyond Twilio console.

## Twilio Configuration
- Settings to add in `django_chores/settings.py` or env vars:
  - `TWILIO_ACCOUNT_SID`: Twilio account SID (from console).
  - `TWILIO_AUTH_TOKEN`: Auth token (store in secrets, not version control).
  - `TWILIO_FROM_NUMBER`: Sending number (E.164, must be provisioned in Twilio).
  - `TWILIO_ENABLED`: Boolean toggle (default False) to enable SMS sending; stub if disabled.
  - `TWILIO_MAX_DAILY_SENDS`: Optional cap per day to prevent runaway costs.
- Install `twilio` Python SDK: add `twilio` to `requirements.txt`.
- Credentials stored in `.env` (never committed) or deployment secrets manager; validate at startup.

## Implementation: `send_sms()` in `core/reminders.py`
Replace the `NotImplementedError` stub with:

1. **Validation**:
   - Check `settings.TWILIO_ENABLED`; log and return if False.
   - Verify `reminder.phone_e164` is set and user has `sms_notifications_enabled=True` and `sms_opted_out_at=None`.
   - Fetch user record to confirm opt-in; skip if opted out or disabled.

2. **Message Formatting**:
   - Subject + message: combine `reminder.subject` (if set) and `reminder.message` into a single string.
   - Truncate to 160 chars to avoid multi-segment fees; prioritize message over subject if length exceeds.
   - Include short action link: append `reminder.action_link` if available; use URL shortener if needed to fit within limit.
   - Example: "Chore due: Take out trash by 6pm. View: https://short.link/abc123"

3. **Twilio Client**:
   - Instantiate `twilio.rest.Client(account_sid, auth_token)` (reuse singleton or per-call).
   - Call `client.messages.create(from_=TWILIO_FROM_NUMBER, to=reminder.phone_e164, body=formatted_message)`.
   - Capture response `sid`, `status`, and `error_code` if any.

4. **Error Handling**:
   - Catch Twilio exceptions (`TwilioRestException`): invalid number, unverified number (trial mode), insufficient balance.
   - Log error with `user_id`, `household_id`, and exception message; do not retry automatically to avoid spam.
   - Return gracefully; do not block other reminder channels (email/HA) if SMS fails.

5. **Logging & Audit**:
   - Log successful sends: `user_id`, `household_id`, `to`, `sid`, timestamp.
   - Optional: create `SMSLog` record if model exists for compliance audit.
   - Track daily send count in cache (Redis or Django cache) to enforce `TWILIO_MAX_DAILY_SENDS`; reject if exceeded and alert admin.

6. **Respect Quiet Hours & Cooldown**:
   - Quiet hours enforcement: handled by `dispatch_reminder()` or task layer before calling `send_sms()`.
   - Cooldown: check last SMS send timestamp per user; skip if within cooldown window; log skip.

## Opt-Out & TCPA Compliance
- STOP keyword handling:
  - Twilio inbound webhook: create Django endpoint `/api/webhooks/twilio/sms/` to receive inbound messages.
  - Parse body for keywords: "STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT" (case-insensitive).
  - If matched, set `user.sms_opted_out_at = now()` and `user.sms_notifications_enabled = False`; save user.
  - Reply with confirmation: "You have been unsubscribed from SMS notifications. Reply START to opt back in."
- START keyword re-opt-in:
  - Parse "START", "SUBSCRIBE", "YES"; if matched, clear `sms_opted_out_at` and set `sms_notifications_enabled = True`.
  - Reply: "You have been re-subscribed to SMS notifications."
- Webhook security: validate `X-Twilio-Signature` header to ensure requests are from Twilio.
- User-initiated opt-in/opt-out: add toggle in user profile settings; log changes for audit.
- Include footer in messages: "Reply STOP to unsubscribe" (if space permits).

## Admin & UI Surfaces
- User profile page (`/profile/`):
  - Phone number field (E.164 format, with country code); validation on save.
  - Checkbox "Enable SMS notifications" (default unchecked); disabled if opted out.
  - Display opt-out status if `sms_opted_out_at` is set; button to clear opt-out (admin-only or self-serve).
- Admin hub (Admin-only):
  - Edit phone numbers for household members (including children).
  - View SMS send logs (if `SMSLog` model exists) per user/household.
  - Dashboard widget showing daily SMS send count and cost estimate (if Twilio pricing API integrated).
- Household settings:
  - Option to disable SMS for entire household (override user settings) if needed.

## Cost Control & Rate Limiting
- Twilio pricing: ~$0.0079 USD per SMS (US domestic); higher for international. Document expected monthly cost based on household count and reminder frequency.
- Daily send cap: `TWILIO_MAX_DAILY_SENDS` setting (e.g., 1000); track in Redis/cache with daily reset.
- Per-user throttle: enforce cooldown (`REMINDER_COOLDOWN_MINUTES`) to prevent spam; skip sends if last SMS was within window.
- Alert on threshold: if daily sends reach 90% of cap, email admin or create in-app notification.
- Billing alerts: configure in Twilio console to email if spend exceeds threshold.

## Testing & Validation
- Unit tests for `send_sms()`:
  - Mock Twilio client; verify message formatting, truncation, error handling.
  - Test opt-out/opt-in logic; ensure opted-out users are skipped.
  - Validate E.164 phone number format in model/form.
- Integration tests:
  - Twilio sandbox (trial account): test real sends to verified numbers.
  - Webhook handler: simulate inbound STOP/START messages; verify DB updates and replies.
- Load testing:
  - Simulate 100+ simultaneous SMS sends; verify rate limiting and cooldown enforcement.
  - Check daily cap enforcement; ensure sends are blocked after cap and reset at midnight.
- International testing: test with international numbers (if supported); document geo-permission setup in Twilio.

## Privacy & Security Considerations
- Phone number PII: treat as sensitive; restrict visibility in admin UI to household admins only.
- Encryption: store phone numbers in DB plaintext (Django default); consider field-level encryption if required by compliance.
- Access control: only household admins and account owners can view/edit phone numbers; children's numbers editable by admins only.
- Audit logs: log phone number changes (who, when, old/new value) in `User` audit trail if model supports it.
- GDPR/CCPA: document phone number collection in privacy policy; provide deletion on account removal; export in data subject requests.
- Twilio data retention: configure message retention in Twilio console; note that Twilio logs messages for compliance.

## Implementation Steps
1. Add `User` model fields (`phone_number`, `sms_notifications_enabled`, `sms_opted_out_at`); create migration.
2. Install `twilio` SDK; add settings for SID, auth token, from number, and enabled flag; validate at startup.
3. Implement `send_sms()` in `core/reminders.py`: format message, call Twilio API, handle errors, log sends.
4. Create opt-out webhook endpoint `/api/webhooks/twilio/sms/`; parse STOP/START keywords, update user, reply.
5. Add phone number and SMS toggle to user profile UI; validate E.164 format in forms.
6. Build admin UI for phone number management and SMS logs (if `SMSLog` model added).
7. Implement rate limiting: daily send cap in cache; per-user cooldown checks.
8. Write tests: unit tests for `send_sms()`, integration tests with Twilio sandbox, webhook handler tests.
9. Document Twilio setup in `README` or `REMINDER_NOTES`: account creation, number provisioning, env vars, international setup.
10. Update privacy policy to document phone number collection and SMS opt-in/opt-out.

## Optional Future Enhancements
- **MMS support**: send photo attachments (e.g., chore completion photos) via MMS; requires Twilio MMS-enabled number.
- **Two-way SMS**: allow users to reply with keywords to mark chores complete (e.g., "DONE #123").
- **Delivery status webhooks**: receive Twilio status callbacks (delivered, failed, undelivered); update `SMSLog` with final status.
- **Shortcode or branded sender**: use Twilio short code or alphanumeric sender ID (if available in region) for brand recognition.
- **Cost reporting**: integrate Twilio Usage API to show real-time cost in admin dashboard.
- **Localized messaging**: support multi-language SMS content based on user locale.

## Open Questions
- Do we support international SMS in phase 1, or restrict to US/Canada only?
- Should phone numbers be unique per user globally, or allow shared numbers within a household (e.g., parent phone for multiple children)?
- Do we need a separate `SMSLog` model, or rely on Twilio console logs and in-app `Notification` records?
- Should admins be able to send manual test SMS from the admin UI?
- How do we handle landline numbers (Twilio rejects them)? Show validation error and require mobile?
