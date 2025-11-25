# Rewards Plan

Structured plan for a richer rewards system: data model upgrades, flows, UI, services, and tests.

## Goals
- Make rewards safe against double-spend, stock races, and child-role abuse.
- Provide clear admin workflows (create, approve/deny/fulfill, restock).
- Give members a clean browse/redeem experience with instant feedback.
- Log points and status history for auditability.

## Data Model (additions/changes)
- `Reward`:
  - `category` (existing) plus optional `tags` (array/CSV) for filtering.
  - `is_featured` flag for front-page highlighting.
  - `per_user_limit` (replace/alias `max_redemptions_per_user`) and optional `cooldown_days`.
  - `low_stock_threshold` (int) to trigger admin alert.
  - `requires_approval` bool (default true for child role, configurable for others).
  - `instructions` text (pickup/delivery notes).
  - `image` or keep `icon`.
  - Invariants: non-negative quantities, `quantity_remaining <= quantity_available`, `point_cost > 0`.
- `RewardRedemption`:
  - Statuses: `pending`, `approved`, `denied`, `fulfilled`, `cancelled`.
  - Fields: `requested_at` (alias created), `processed_by`, `processed_at`, `fulfilled_by`, `fulfilled_at`, `decision_note`, `proof_image` (optional), `user_note`.
  - `refund_points` boolean for cancellations/denials; `refunded_at`.
  - Unique constraint to respect per-user limit across a rolling window when enforced via query + check.
- `PointTransaction`:
  - Ensure reward redemptions log as `spent`, refunds as `bonus/refund` with `source_type='reward'`.

## Service Layer (new `services/rewards.py`)
- `request_redemption(user, reward, household)`: validates membership, availability, limits, stock; deducts points atomically; creates redemption + transaction.
- `approve_redemption(redemption, actor)`: re-check stock, mark approved, decrement remaining, log decision.
- `deny_redemption(redemption, actor, refund=True, reason=None)`: mark denied, refund if configured.
- `fulfill_redemption(redemption, actor, note=None)`: mark fulfilled; optional proof capture hook.
- `cancel_redemption(redemption, actor, refund=True)`: member/admin cancel; refund if pending/approved and allowed.
- Helpers: `ensure_available(reward, user)`, `enforce_user_limit(...)`, `should_refund(...)`.
- All functions wrapped in `transaction.atomic()` with `select_for_update()` on reward to avoid races.

## Views/API (household-scoped)
- Member UI/API:
  - List rewards with filters: availability, category/tags, cost sort, featured.
  - Reward detail: description, cost, remaining, per-user rules, instructions.
  - Redeem action (POST) -> creates pending or auto-approved based on rules.
  - My redemptions list with status/history; allow cancel when pending.
- Admin UI/API:
  - Reward CRUD (stock, cost, windows, limits, featured, requires approval).
  - Redemption inbox: filter by status, approve/deny with note, fulfill, cancel/void, refund toggle.
  - Stock actions: restock, set quantity, toggle active, regenerate invite link to reward? (optional).
  - Low-stock banner if `quantity_remaining <= threshold`.

## Permissions & Rules
- Membership required; household scoping on all queries.
- Child role: always `requires_approval=True`; cannot auto-approve.
- Admins/staff can approve/deny/fulfill; members only request/cancel their own.
- Keep at least zero stock; deny if out-of-stock or outside availability window.
- Per-user limits: deny once limit reached; optional cooldown uses `created_at` window filter.

## Notifications
- To member: request received, approved, denied (with reason), fulfilled, cancelled/refunded.
- To admins: new request; low-stock alert.

## UI Notes
- Reward gallery cards: title, cost, remaining badge, availability (upcoming/active/ended), featured highlight, Redeem CTA disabled when not eligible.
- Detail modal/page: description, instructions, limits, your past redemptions.
- Admin table: inline status actions, quick notes, stock pills, filters by status/category.

## Tests
- Services: request -> approve flow deducts points and stock; deny refunds points; cancel pending refunds; last-item race with `select_for_update`.
- Limits: per-user limit and cooldown enforced; availability window respected; low-stock alert trigger.
- Permissions: member vs admin actions; child role requires approval.
- UI/API: list only household rewards; redeem blocked when insufficient points or out-of-stock.

## Migration steps (later)
- Add new fields to `Reward` and `RewardRedemption` with defaults.
- Backfill `quantity_remaining` where null from `quantity_available`.
- Add constraints and indexes: `Reward(household, is_active, available_until)`, `RewardRedemption(reward, user, status)`.
