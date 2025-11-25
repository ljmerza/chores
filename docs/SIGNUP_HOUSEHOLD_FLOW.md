# Signup + Household Entry Changes

Notes for shifting signup so every new account either creates a household or joins one with an invite code. Remove the empty-database setup shortcut and keep the database model support for multiple households, but restrict new signups to one household.

## Current behavior (implemented)
- `/` and `/login/` no longer redirect to `/setup/` when the database is empty. The setup wizard is still available at `/setup/` but is not auto-triggered.
- A public choice page (`SignupChoiceView` → `templates/core/signup_choice.html`) funnels users to either create or join.
- Creating a household uses `HouseholdSignupView` + `HouseholdSignupForm` (shares fields/validation with `SetupWizardForm` but does not grant staff/superuser). The flow creates the user (role `admin`), household, membership, and `UserScore`, then logs in the user.
- Joining with an invite uses a two-step verify flow: `InviteCodeView` + `InviteCodeForm` validate/store the household id in the session, then `InviteSignupView` + `InviteAccountForm` create the user (role `member`), membership, and `UserScore` before logging in.
- All public signup routes are open regardless of existing households; accounts are created only through “create household” or “join with invite” paths.

## Flow details
- Create a household
  - Entry point: `/signup/` → “Create a household” → `HouseholdSignupView`.
  - Collect account fields (username, password, names, optional email) and household fields (name, optional description).
  - On submit: create the user, household, membership as `admin`, and `UserScore`. Log the user in and route to the dashboard.
  - Keep the user role/membership admin, but do not automatically grant staff/superuser. Reserve `is_staff`/`is_superuser` for explicit admin creation.
- Join with invite code (verify flow)
  - Step 1: `/invite/` (`InviteCodeView`) captures invite code, normalizes/validates, and stores the verified household id in the session.
  - Step 2: `/invite/signup/` (`InviteSignupView`) shows household details, collects account fields, creates the user/membership/score as `member`, then logs in.
  - If the session household is missing/invalid, the flow redirects back to the invite-code page.

## Implementation outline
- Routing/views/templates
  - Signup choice: `SignupChoiceView` → `templates/core/signup_choice.html`.
  - Create household: `HouseholdSignupView` → `templates/core/signup_create_household.html` using `HouseholdSignupForm`.
  - Join with invite: `InviteCodeView` (`templates/core/invite_code.html`) validates code, then `InviteSignupView` (`templates/core/invite.html`) handles account creation with `InviteAccountForm`.
  - Removed `User.objects.exists()` gating from `HomeView`, `LoginView`, and invite dispatch; `/setup/` remains for the legacy wizard but is no longer auto-linked.
- Forms/validation
  - Invite flows use `InviteCodeForm` (code lookup, sets `form.household`) and `InviteAccountForm` (username/email uniqueness checks, password validation).
  - Household creation uses `HouseholdSignupForm` (same validation as `SetupWizardForm`) without auto staff/superuser flags.
  - Signup routes are restricted to unauthenticated users, and each flow creates exactly one household membership for the new user.
- UX/content updates
  - Navbar/home/login point to the new signup entry points instead of `/setup/`.
  - Invite verification step shows household name/description/code before account creation.

## Acceptance checks
- Visiting `/` or `/login/` on an empty database loads the normal home/login page; no forced redirect to `/setup/`.
- New users can create a household via the new signup page and land on the dashboard as household admins.
- New users can join with an invite code via the verify flow, see the household name, confirm, and land on the dashboard as members.
- Attempting to reuse signup to join/create another household with the same user is blocked (UI error + server-side guard).
- Existing multi-household data remains valid; admin tooling can still manage multiple memberships where needed.
