# Chore Due Rule Plan

Plan for representing and generating due dates for chores, including interval rules, day-of-week/month rules, and month-based filters.

## Core Shape
- Use existing `Chore.recurrence_pattern` for the base type: `none`, `daily`, `weekly`, `biweekly`, `monthly`, `custom`.
- Standardize `recurrence_data` keys:
  - `start_date` (ISO date) and optional `due_time` (HH:MM) with `timezone`.
  - `end_date` or `max_occurrences` guards.
  - `rule` payload (varies by pattern).
  - `filters`: `allowed_months` (ints 1-12), `exclude_dates`, optional `include_dates` (one-offs).

## Pattern Definitions
- `none`: one-time chore, relies solely on `due_date`.
- Interval (every _N_ days):
  - `recurrence_pattern`: `daily` (or `custom` if preferred).
  - `rule`: `{ "type": "interval_days", "every": 3 }` (3 = every three days).
- Weekly / day-of-week:
  - `recurrence_pattern`: `weekly`.
  - `rule`: `{ "days_of_week": [1, 4], "interval_weeks": 1 }` (Mon/Thu every week). Store days 0-6 = Mon-Sun.
- Biweekly:
  - `recurrence_pattern`: `biweekly`.
  - `rule`: `{ "days_of_week": [5], "interval_weeks": 2, "anchor_week": "start_date" }` (Saturday every other week).
- Monthly (calendar day):
  - `recurrence_pattern`: `monthly`.
  - `rule`: `{ "day_of_month": 15, "roll_strategy": "last_day" }` (15th; if month shorter, use last day).
- Monthly (nth weekday):
  - `recurrence_pattern`: `monthly`.
  - `rule`: `{ "nth": 2, "weekday": 0, "mode": "nth_weekday" }` (second Monday each month). Support `nth = -1` for “last”.
- Custom / mixed (multiple specific days):
  - `recurrence_pattern`: `custom`.
  - `rule`: `{ "specific_days_of_month": [1, 15, 28] }` or `{ "custom_dates": ["2024-12-24"] }`.

## Month Filters
- Apply after candidate generation: if `allowed_months` is set and the candidate month is not included, skip to the next interval.
- Examples:
  - Summer-only chore: `allowed_months: [6, 7, 8]`.
  - School-year chore: `allowed_months: [9,10,11,12,1,2,3,4,5]`.

## Generation Flow
1) Start from `start_date` (respect `timezone` and `due_time` when setting `due_date` on instances).
2) Produce the next candidate date using the pattern-specific rule.
3) Apply filters: `allowed_months`, `exclude_dates`, and optional `include_dates` overrides.
4) Stop when `end_date` is reached or `max_occurrences` emitted.
5) Create `ChoreInstance` rows with the resolved `due_date` and assignment info.

## Examples
- Every 3 days: `recurrence_pattern: "daily"` + `rule: { "type": "interval_days", "every": 3 }`.
- Every Tuesday: `recurrence_pattern: "weekly"` + `rule: { "days_of_week": [1], "interval_weeks": 1 }`.
- Every 1st and 15th, only Jun-Aug: `recurrence_pattern: "custom"` + `rule: { "specific_days_of_month": [1,15] }` + `filters: { "allowed_months": [6,7,8] }`.
- Last Saturday of each month during the school year: `recurrence_pattern: "monthly"` + `rule: { "nth": -1, "weekday": 5, "mode": "nth_weekday" }` + `filters: { "allowed_months": [9,10,11,12,1,2,3,4,5] }`.
