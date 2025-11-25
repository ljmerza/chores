# Agents Guide

Working notes to ramp up quickly on the Chore Manager project. Covers what the app does, tech stack, how to run it, key code hotspots, and where the deeper docs live.

## What the project is
- Django-based household chore manager with gamification: points, streaks, leaderboards, and rewards.
- Supports multiple households with invite codes, roles (admin/member/child), and per-household scores.
- Chores can be assigned, global (claimable), or rotating; support one-time/recurring schedules, due dates, and photo verification.
- Transfers between users, notifications, and streak bonuses; rewards catalog with redemption and approval flow.
- Server-rendered templates (Tailwind CDN) plus a nascent service layer; API auth not implemented yet (all endpoints are currently open—lock down before production).

## Stack and dependencies
- Django 5.2, Django REST Framework, Pillow (images), django-filter, django-cors-headers, python-decouple for env handling.
- Optional UI helpers: django-crispy-forms + crispy-bootstrap5.
- Databases: MySQL 8 by default (Docker), PostgreSQL and SQLite also work; `mysqlclient` and `psycopg2-binary` included.
- Deployment/runtime: Gunicorn (prod), Docker + docker-compose. Future tasks commented in `requirements.txt` for Celery/Redis scheduling.
- Frontend: Django templates with Tailwind CDN. Static/media volumes are mounted in Docker.

## How to run
- Docker (default): `docker-compose up --build` then open the mapped port (see `docker-compose ps`; repo currently maps 9478 -> 8000). Auto-runs migrations. App starts in debug mode with permissive hosts and default secret key—replace for real deployments.
- Local: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env`, configure DB env vars, run `python manage.py migrate` and `python manage.py runserver`. Always use the venv (or Docker); avoid mixing global Python installs.
- Seed demo data: `./scripts/seed_demo_data.sh [--force]` (runs in Docker `web` service if present, otherwise locally). Demo users are created with password `demo1234`.
- Stop/clean: `docker-compose down` (add `-v` to remove DB + volumes).

## Code layout (core hotspots)
- `choremanager/`: project settings/urls; Tailwind pulled via base template.
- `core/`: custom email-based `User`, setup wizard views, forms, and `services/`:
  - `services/points.py`: `adjust_points` (atomic balance + transaction update, guards against zero/invalid/negative spend).
  - `services/chores.py`: `complete_chore_instance` (state guard, awards points, creates notification).
  - `services/notifications.py`: `create_notification` stub for in-app rows only.
  - `reminders.py`: channel stubs (email/SMS/Home Assistant/push) with `ReminderTarget`; meant to be called from future Celery tasks.
- `households/`: `Household` (unique invite codes), `HouseholdMembership`, `UserScore`, `PointTransaction`, `Leaderboard`. Check constraints enforce non-negative scores and balance.
- `chores/`: `ChoreTemplate`, `Chore` (assignment types, recurrence fields, priority, verification flags), `ChoreRotation`, `ChoreInstance` (status tracking, photos, due dates), `ChoreTransfer`, `Notification`.
- `rewards/`: `Reward` (stock, availability windows, per-user limits, approval flags, tags, images) and `RewardRedemption` (pending/approved/denied/fulfilled/cancelled with audit fields).
- Templates: shared components in `templates/components/` (buttons, badges, alerts, cards, etc.) documented in `docs/PLANNING.md`.
- Tests: service and model guards live in `core/tests.py` and `chores/tests.py` (points invariants, completion flow).
- Scripts: `scripts/seed_demo_data.sh` runs `manage.py seed_demo_data` inside Docker or locally.

## Planning & reference docs
- `README.md`: high-level features, stack, quick start, project tree, and model list.
- `docs/PLANNING.md`: component catalogue (`templates/components/*`), feature overview, and a full schema outline with future ideas.
- `docs/SERVICES.md`: explains the service-layer modules and current tests.
- `docs/CHORE_DUE_RULES.md`: recurrence data shape for generating chore due dates, including monthly/nth-weekday rules and month filters.
- `docs/REMINDER_NOTES.md`: Celery-driven reminder design, channel data needs, env knobs, and implementation checklist for `core/reminders.py`.
- `docs/REWARDS_PLAN.md`: roadmap for hardening rewards (stock races, approvals, limits), planned `services/rewards.py`, notifications, and tests.
- `docs/IMPROVEMENT_PLAN.md`: backlog of invariants/indexes, DRF API/auth hardening, Celery scheduling, DX/CI items, and setup flow tightening.

## Known gaps and cautions
- API endpoints lack authentication/authorization—treat everything as public until locked down.
- Reminder dispatch and Celery scheduling are stubs; background jobs are not wired.
- Tailwind uses CDN; production pipeline not configured (see `docs/IMPROVEMENT_PLAN.md` for build/WhiteNoise/S3 ideas).
- Secrets: Docker defaults include an insecure `SECRET_KEY` and open `ALLOWED_HOSTS`; replace for any non-local use.
