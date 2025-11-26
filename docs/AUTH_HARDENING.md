# Auth & API Hardening Plan

Implementation checklist to require authentication everywhere, scope DRF endpoints to households, guard invites/join, and hide admin actions in templates.

## Goals
- Require login for all non-public pages and APIs by default.
- Ensure every API endpoint is household-scoped and enforces membership/admin roles.
- Block abuse of invite/join flows and prevent multi-household signups through the public funnel.
- Prevent UI leakage of admin controls to non-admins.

## Auth Baseline
- Settings: set `LOGIN_URL`/`LOGIN_REDIRECT_URL`; default `REST_FRAMEWORK.DEFAULT_PERMISSION_CLASSES = [IsAuthenticated]` (override only for public endpoints like signup/invite).
- Views: apply `LoginRequiredMixin` to class-based views and `@login_required` to function views; keep an allowlist (home, signup choice, invite verify/signup, password reset, static/media).
- Tests: anonymous users hitting protected views are redirected; allowlist remains public.

## DRF Household Permissions
- Permissions module (`core/api/permissions.py`):
  - `IsHouseholdMember`: asserts the request user has a membership on the target household (from object, serializer context, or URL kwarg).
  - `IsHouseholdAdmin`: same as above but requires admin role.
- Base viewset mixin (`BaseHouseholdViewSet` or `HouseholdScopedMixin`):
  - Filters `queryset` to households the user belongs to, or to `household_pk` when using nested routers.
  - On create, sets `household` from URL/serializer context; validates membership before save.
- Apply to viewsets: households, members, chores, chore instances (and actions: claim/start/complete/verify/transfer), rewards, redemptions, notifications, transactions/score.
- Tests:
  - Member sees only their household data; other households return 404/403.
  - Admin-only actions blocked for members; non-members blocked everywhere.

## Invite/Join Guards
- If authenticated, block access to public signup/invite routes (redirect with message).
- When joining via invite: verify code/session household match; prevent enumeration (generic errors, optional throttle).
- Enforce single membership for signup path: if a user already has a membership, do not create another via public flows.
- Ensure `HouseholdMembership` uniqueness is enforced (constraint exists).
- Tests: logged-in user cannot hit invite/signup; duplicate join attempts fail cleanly.

## Template-Level Permission Checks
- Add helper/tag (e.g., `has_household_role user household "admin"`) or context processor to expose `membership_role`.
- Hide admin-only buttons/links (member management, approvals, chore verify/transfer overrides, reward approvals) for non-admins.
- Tests: render templates as member vs admin and assert admin controls appear/disappear accordingly.

## Additional Considerations
- CSRF remains enabled for session-auth APIs; keep DRF session auth for now (JWT later if needed).
- Optionally add throttling for login/invite endpoints to reduce abuse.
- Document allowlist/public routes in `README` after implementation.
