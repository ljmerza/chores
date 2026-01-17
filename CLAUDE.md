# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django-based household chore manager with gamification (points, streaks, leaderboards, rewards). Multi-household support with invite codes, roles (admin/member/child), and per-household scoring.

## Common Commands

### Docker (primary development method)
```bash
docker-compose up --build          # Start all services (web on :9478, flower on :5555)
docker-compose down                # Stop services
docker-compose down -v             # Stop and remove all data
docker-compose logs web            # View web service logs
docker-compose exec web python manage.py shell  # Django shell
```

### Helper Scripts (auto-detect Docker vs local)
```bash
./scripts/makemigrations.sh [app]  # Create migrations
./scripts/run_migrations.sh        # Apply migrations
./scripts/seed_demo_data.sh        # Load demo data (password: demo1234)
```

### Testing
```bash
# Docker
docker-compose exec web python manage.py test

# Local
python manage.py test                    # All tests
python manage.py test core.tests         # Single app
python manage.py test core.tests.PointsServiceTests.test_award_points_updates_score_and_transaction  # Single test
```

### Local Development
```bash
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                     # Configure MYSQL_HOST="" for SQLite
python manage.py migrate
python manage.py runserver
```

### Celery (background tasks)
```bash
# Local (requires Redis)
celery -A choremanager worker -l info
celery -A choremanager beat -l info
```

## Architecture

### Django Apps
- **core/**: Custom email-based User model, setup wizard, context processors
- **households/**: Household, HouseholdMembership, UserScore, PointTransaction, Leaderboard, StreakBonus
- **chores/**: Chore, ChoreInstance, ChoreTemplate, ChoreTransfer, ChoreRotation, Notification
- **rewards/**: Reward, RewardRedemption (with approval workflow)

### Service Layer (`core/services/`)
Business logic is centralized here rather than in views:
- `points.py`: `adjust_points()` - atomic balance updates with `InvalidAmountError`, `NegativeBalanceError` guards
- `chores.py`: `complete_chore_instance()` - state validation, point awards, notification creation
- `notifications.py`: `create_notification()` - in-app notification stub

### Background Tasks (`chores/tasks.py`)
Celery beat scheduled tasks:
- `scan_due_items`: Find due/overdue chores, emit notifications, mark expired
- `send_scheduled_chore_digests`: Digest notifications
- `generate_recurring_instances`: Create upcoming instances for recurring chores
- `recompute_streaks_and_leaderboards`: Daily streak/leaderboard rollup

### Template Components (`templates/components/`)
Reusable UI components: `button.html`, `badge.html`, `alert.html`, `card.html`, `stat_tile.html`, `section_header.html`, `empty_state.html`, `form_field.html`, `messages.html`, `navbar.html`

### Database
- Docker default: MySQL 8.0 (internal, no exposed port)
- Local: Set `MYSQL_HOST=""` in `.env` to use SQLite

## Key Patterns

### Points System
Points use difficulty multipliers (easy=1x, medium=2x, hard=3x, expert=5x). All point changes go through `adjust_points()` which enforces non-negative balances and creates audit transactions.

### Chore Instances
Recurring chores generate `ChoreInstance` records. Instance status flow: available -> claimed/in_progress -> completed -> verified (if required) or expired.

### Reminder Channels (`core/reminders.py`)
Channel stubs for notifications: email, SMS, Home Assistant, push. Home Assistant works when configured; others are placeholders.

## Known Limitations

- API endpoints lack authentication (all open - lock down before production)
- Tailwind uses CDN (no build pipeline)
- Docker uses insecure SECRET_KEY and `ALLOWED_HOSTS=*` - replace for non-local use
