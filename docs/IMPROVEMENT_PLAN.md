# Chore Manager Improvement Plans

Plans to deliver each suggested change. Each section lists objectives, concrete steps, and key decisions/risks to resolve before implementation.

## 1) Model Invariants & Indexes
- Objectives: enforce non-negative values, prevent duplicate invite codes, add useful indexes.
- Steps:
  - [x] Convert point/quantity fields to `PositiveIntegerField` or add `CheckConstraint` where negatives are allowed (e.g., penalties) but need bounds. (Most in place; `Leaderboard.points/chores_completed/rank` and `PointTransaction.balance_after` now enforced as non-negative.)
  - [x] Add `clean()` validations for `Reward` and `Chore` point ranges; keep `save()` logic to backfill `quantity_remaining` on create (backfill is in place).
  - [x] Implement an invite-code regeneration loop to guarantee uniqueness on `Household` creation/regeneration.
  - [x] Add DB index: `Chore(household, status, priority)`.
  - [ ] Add DB index: `ChoreInstance(household via chore, status, due_date)` (current indexes cover status/due_date only; household scope still missing).
  - [x] Add DB index: `Leaderboard(household, period)`.
  - [x] Add DB index: `PointTransaction(user, created_at)`.
  - [x] Create and run migrations; add minimal model tests for constraints and invite-code uniqueness.
- Decisions/Risks: allow negative `PointTransaction.amount` for penalties? If yes, use constraints per transaction type instead of strict positive fields.

## 2) Service Layer for Business Rules
- Objectives: centralize side effects (points, scores, notifications).
- Steps:
  - [x] Create `services/` package with modules: `points.py` (award/spend, transaction logging, streak updates), `chores.py` (state transitions, verification), `notifications.py` (enqueue/send).
  - [ ] Move logic from views/serializers into services with idempotent functions; return typed results (e.g., dataclass with updated models). (Service functions exist and are used in tests/seed data; views like `complete_chore` still update state inline.)
  - [ ] Add unit tests around services to cover chore completion, transfers, reward redemption, and error cases. (Points/chore completion/reward redemption covered; transfer flow still missing.)
- Decisions/Risks: decide synchronous vs async notifications; define error taxonomy (custom exceptions) for consistent API responses.

## 3) DRF API Endpoints
- Objectives: expose household-scoped CRUD and actions with proper authz.
- Steps:
  - [ ] Add serializers/viewsets/routers for households, chores, chore instances/actions (claim/start/complete/verify/transfer), rewards, redemptions, notifications.
  - [ ] Implement household-scoped permissions (e.g., custom `IsHouseholdMember`, `IsHouseholdAdmin`) and enforce membership in querysets.
  - [ ] Add filters/search/orderings matching PLANNING.md; enable pagination defaults already configured.
  - [ ] Write API tests for core flows: create household, assign/complete chore, award points, redeem reward, list notifications.
- Decisions/Risks: choose between session vs JWT for the SPA; confirm which actions are admin-only vs member-accessible.

## 4) Background Jobs & Scheduling
- Objectives: offload recurring work and reminders.
- Steps:
  - [x] Add Celery + Redis config (worker + beat) and tasks for due/overdue reminders plus basic recurrence generation.
  - [ ] Implement streak recalculation and leaderboard rollup tasks (not yet wired).
  - [x] Wire periodic schedules in `celery.py`/`celerybeat` settings and docker-compose.
  - [ ] Ensure tasks call service-layer functions and are idempotent (use locks or check states).
  - [ ] Add smoke tests for tasks (e.g., daily job creates instances and sends reminders).
- Decisions/Risks: pick broker/result backend (Redis vs database); rate-limit notifications to avoid spam.

## 5) Auth & Setup Flow Improvements
- Objectives: tighten public surface and support invites.
- Steps:
  - [ ] Require login for all app views; keep `/setup/` only when no users exist.
  - [ ] Add invite/join endpoints and simple UI to accept invite codes; prevent membership enumeration. (Invite signup flow exists; needs enumeration/abuse hardening.)
  - [x] Provide a lightweight login/register page (or API) instead of routing users to `/admin/`.
  - [ ] Add household-aware permission checks in templates if keeping server-rendered pages.
- Decisions/Risks: enforce one-owner policy vs multiple admins; clarify password policies and email verification needs.

## 6) DevOps & DX Polishing
- Objectives: harden deploys and improve developer workflow.
- Steps:
  - [ ] Remove default `SECRET_KEY` and document required env vars; expand `.env.example` (defaults still present in settings and docker-compose).
  - [ ] Add WhiteNoise for static files and optional S3/media storage configuration.
  - [ ] Introduce Tailwind build pipeline (npm + PostCSS) for production instead of CDN.
  - [ ] Add pytest + factory_boy, coverage config, and a minimal CI workflow (lint, tests, migrations check).
  - [ ] Update Docker/Docker Compose to include Celery services and static collection step (Celery worker/beat/flower already included; still need collectstatic).
- Decisions/Risks: choose testing database (SQLite vs MySQL) for CI; decide on error monitoring (Sentry) and logging format for containers.
