# Household Chore Reminder Scheduling Plan

Plan for allowing household admins (only) to choose when each member gets notified about due chores on each day of the week. Focus is on predictable digests tied to local time, with guardrails for spam and overdue catch-up.

## Goals & Scope
- Admins configure per-user schedules (day-of-week -> exactly one time) for chore due reminders.
- Reminders summarize chores due soon/overdue for that user within the household; avoid spamming outside configured times.
- Respect household/user time zones and existing reminder cooldown/quiet-hour knobs.
- Phase 1 excludes ad-hoc one-off overrides, cross-household bulk edits, and non-chore notification types.

## Assumptions & Decisions to Lock
- Time zone source: add `Household.timezone` (IANA); allow per-user override later if needed.
- Lead window: include chores due or overdue within the next `REMINDER_LEAD_TIME_MINUTES` (existing setting) relative to the scheduled send time.
- Default behavior: if no schedule exists for a member, fall back to the current immediate scan (`scan_due_items`) to avoid regressions.
- Channel delivery still flows through `core.reminders.dispatch_reminder`; schedule only gates when we call it.

## Defaults & Backfill Plan
- Default send time: 18:00 local time for all days.
- New households: auto-create a `ReminderSchedule` for each member (and for members added later) with 18:00 on all days, active=true.
- Existing households: data migration/backfill to set `Household.timezone` to `settings.TIME_ZONE` when empty and create schedules for current members using the 18:00 default; skip households with explicit schedules if any exist.
- Admins can edit or disable per-member schedules after the default is created; no member self-serve.

## Data Model Changes
- `Household.timezone` (CharField, default to settings.TIME_ZONE) to anchor schedule evaluation.
- `ReminderSchedule` (new model, likely in `households` or `core`):
  - `household` FK, `user` FK (unique together).
  - `per_day_time` JSON: `{"mon":"18:00", "tue":"18:00", ...}` storing one 24h HH:MM string per day; null/missing = no send that day.
  - `active` boolean, `default_channel_order` optional list to override `preferred_channels`.
  - Audit fields (`created_at/updated_at`, `created_by` admin FK).
- Optional future: `ReminderSendLog` or reuse `Notification` for last-sent tracking; for now leverage cooldown + in-memory windowing.

## Scheduler & Delivery Logic
- New Celery task `send_scheduled_chore_digests` runs every 5 minutes.
- For each household with schedules:
  - Resolve tz (`household.timezone`); compute current local day/time and find schedules within a tolerance window (e.g., now ±2.5 minutes).
  - For each user scheduled now:
    - Query active `ChoreInstance`/`Chore` assigned to that user in the household with `due_date` ≤ scheduled time + lead window; include overdue items.
    - Skip if no items or if a digest for this user/day/time was sent within cooldown (`REMINDER_COOLDOWN_MINUTES`).
    - Build a digest notification (title + count, optionally bullet list truncated) and create `Notification` rows (type `chore_due` or `chore_overdue` as appropriate).
    - Call `dispatch_reminder` with aggregated message + action link to "My chores" view.
- Keep existing `scan_due_items` for households/users without schedules; add a guard so scheduled users are excluded from the immediate scan to avoid double sends.
- Honor quiet hours by skipping sends if scheduled time falls inside quiet hours; log skip and try next scheduled window.

## Admin & UI Surfaces
- Household admin-only page (Admin Hub > Notifications):
  - Table of members with per-day single time pickers (no multi-select) and copy-from-template buttons (e.g., "School nights", "Weekends").
  - Toggle to enable/disable schedule per member; inline validation for time format.
  - Preview of effective timezone and link to change household timezone.
- Optional: simple defaults button to set one daily time for all members.
- No user self-serve edits in phase 1; members view-only in profile. Admin-only control is enforced in views/forms.

## API/Service Layer
- Service helpers in `core/services/notifications.py` to:
  - Normalize schedules, merge defaults, and determine next send windows.
  - Generate digest payloads from chore querysets.
  - Record send markers to honor cooldowns.
- Extend serializers/forms (if adding DRF later) to validate HH:MM arrays and day keys.

## Edge Cases & Guardrails
- Membership changes: disable schedules automatically when a user leaves a household; delete or soft-disable rows.
- DST transitions: evaluate schedules in local tz; if a scheduled time is skipped/repeated, send once per unique wall-clock time.
- Overdue accumulation: include overdue items in every digest until completed/expired, but throttle by cooldown.
- Households with no timezone set: use `settings.TIME_ZONE` and warn in UI.
- Missing contact methods: still create in-app `Notification` rows even if external channels cannot send.

## Implementation Steps
1) Add models/migration for `Household.timezone` and `ReminderSchedule`; update admin + forms.
2) Seed defaults: when creating a household, create schedules with a single daily time (18:00) for all members; add signals/hooks to create schedules for new members; data migration to backfill existing households/members with the default schedule.
3) Build service helpers to read schedules, resolve tz, and fetch due/overdue chores for a window.
4) Implement Celery task `send_scheduled_chore_digests`; wire into beat (every 5 min) and add tests for schedule matching, cooldown, and tz handling.
5) Update `scan_due_items` to skip users with active schedules; ensure overdue expiry logic still runs.
6) Create admin UI for editing per-member schedules; add validation and flash messages.
7) Add tests: model validation, service helpers, Celery task behavior, UI form POSTs, and skip logic in `scan_due_items`.
8) Update docs (`README`, `REMINDER_NOTES`) to describe schedules, defaults, and env knobs.

## Open Questions
- Admin-only control is confirmed; no member edits.
- One send time per day is fixed; no multi-send per day.
- Do we need separate schedules for children vs members, or a template system for bulk apply?
