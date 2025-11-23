# Service Layer (Business Logic)

Lightweight service modules that encapsulate core workflows without adding any authentication layer changes.

## Modules
- `core/services/points.py`
  - `adjust_points(...)`: atomic score + transaction update with validation (prevents zero amounts, invalid transaction types, and negative balances). Returns `PointChangeResult` containing updated `UserScore` and `PointTransaction`.
- `core/services/chores.py`
  - `complete_chore_instance(...)`: transitions a `ChoreInstance` to completed, awards points via `adjust_points`, and records a notification. Raises `ChoreStateError` or `MissingAssigneeError` on invalid transitions.
- `core/services/notifications.py`
  - `create_notification(...)`: creates a `Notification` record; channel delivery handled elsewhere.

## Usage Notes
- Call services from views/serializers or tasks to keep side effects consistent.
- API authentication is intentionally not implemented yet; callers should not assume authenticated users until auth is added later.
- Services are synchronous and atomic; background delivery (email/push) remains separate.

## Tests
- Points guards and balance updates: `core/tests.py`
- Chore completion flow (status change, points award, notification creation): `chores/tests.py`
