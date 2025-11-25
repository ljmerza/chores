# Celery + Flower + Chore Scheduler Plan

Working plan to add Celery, Celery Beat, and Flower to the stack and use them to advance chore due states and reminders.

## Goals
- Run background jobs for recurring chore generation and due/overdue scanning.
- Add observability via Flower.
- Keep configuration driven by environment variables for Docker and local runs.

## Stack Decisions
- Broker/Backend: Redis (single instance for broker and result backend).
- Services: `celery` (worker), `celery-beat` (scheduler), `flower` (monitor), all using the Django image/build context.
- Serialization: JSON for tasks/results; timezone-aware (`UTC` or Django `TIME_ZONE`).

## App Wiring
- Add `choremanager/celery.py` with standard Django integration and autodiscovery.
- In `choremanager/__init__.py`, import the Celery app to register tasks on startup.
- Settings: configure `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_SERIALIZER`, `CELERY_ACCEPT_CONTENT`, `CELERY_TIMEZONE`, `CELERY_ENABLE_UTC`, and `CELERY_BEAT_SCHEDULE`.
- Environment: extend `.env.example` with Redis URL, optional Flower auth, reminder knobs (lead/cooldown minutes), and beat intervals.

## Docker Compose Changes
- Add `redis` service.
- Add `celery` worker service: `command: celery -A choremanager worker -l info`, depends on `web`/`redis`.
- Add `celery-beat` service: `command: celery -A choremanager beat -l info`, shares code volume/env with `web`.
- Add `flower` service: `command: celery -A choremanager flower --broker=$CELERY_BROKER_URL --port=5555`, expose port (e.g., 5555).
- Ensure shared environment variables for Celery across services (broker/backend URLs, Django settings module).

## Tasks to Implement
- **Recurrence generator** (`tasks.generate_recurring_instances`):
  - Query `Chore` with `recurrence_pattern != "none"`.
  - Use `recurrence_data` rules (see `docs/CHORE_DUE_RULES.md`) to compute upcoming due dates within a horizon (env-driven, e.g., 14–30 days).
  - Create `ChoreInstance` rows with resolved `due_date`, assignment/rotation, and avoid duplicates (idempotent check by chore/date).
  - Respect end guards (`end_date`, `max_occurrences`) and skip filtered months/dates.
- **Due/overdue scan** (`tasks.scan_due_instances`):
  - Find `ChoreInstance` in statuses `available/claimed/in_progress` with `due_date <= now` (overdue) or `due_date <= now + lead` (due soon).
  - For each, create an in-app `Notification` row and call `core.reminders.dispatch_reminder` (once senders are implemented).
  - Optional: add a lightweight `due_state` flag if we want explicit DB marking; otherwise keep it implicit but record notifications/reminder sends with cooldown.
- **(Optional later)** streak/leaderboard rollups and cleanup tasks.

## Beat Schedule (suggested defaults)
- `generate_recurring_instances`: every 30–60 minutes.
- `scan_due_instances`: every 5–15 minutes, lead window configurable via `REMINDER_LEAD_TIME_MINUTES`.
- Use `CELERY_BEAT_SCHEDULE` in settings with env overrides.

## Testing/Validation
- Unit tests for recurrence generation (sample rules, horizon, idempotency) and due-scan selection logic.
- Integration sanity: `docker-compose up web celery celery-beat flower redis`; ensure tasks appear in Flower and `scan_due_instances` emits notifications for seeded data.
- Document local (non-Docker) commands: `celery -A choremanager worker -l info`, `celery -A choremanager beat -l info`, `celery -A choremanager flower`.

## Open Questions
- Should due/overdue be persisted as a field (e.g., `due_state`) or remain derived with only notifications/reminder logs?
- How many future instances to materialize (fixed window vs. capped count)?
- Reminder cooldown storage: in DB table vs. Redis keys.

## Next Implementation Tasks
- **Streak/leaderboard rollups**
  - Add a Celery task (e.g., `tasks.recompute_streaks_and_leaderboards`) that recalculates per-household streaks and leaderboard standings from recent `ChoreInstance` completions.
  - Update `UserScore` fields (current/longest streak, totals) with `select_for_update()` to avoid races; bulk rebuild `Leaderboard` rows for daily/weekly/monthly/all_time.
  - Schedule via beat (nightly for streaks; hourly/daily for leaderboards); make idempotent and bounded (e.g., last 60 days of completions).
- **Cleanup/maintenance**
  - Add pruning tasks for old data (e.g., `Notification` older than N days, completed/expired `ChoreInstance` older than a window, Celery result backend cleanup if stored).
  - Use configurable retention, batch deletes to reduce locks, and optional beat schedule (weekly) with a disable knob.
- **Reminder cooldown storage choice**
  - Introduce a Redis-backed cooldown check for reminders (key per user/household/type/link with TTL) with DB fallback; configurable backend (`REMINDER_COOLDOWN_BACKEND=redis|db`).
  - Wire into `scan_due_items` to skip duplicate sends when a cooldown key exists; keep current DB check as a safety net.
