# Privacy Statement Planning Notes

Draft outline for a future privacy statement. Tailor to actual deployment choices and confirm with legal counsel. Assumes current code only collects account details provided at signup and stores household activity data in-app; no special handling or data collection for child accounts beyond what is entered.

## What the app does / data it handles (as coded now)
- Account data: username (required), first/last name (optional), email (required for admins/parents; optional/empty for children), password hash.
- Household data: household name/description, invite code, memberships/roles.
- Activity data: chores, completion status/timestamps, points, streaks, rewards, notifications, uploaded photos (if used for verification).
- No analytics, tracking pixels, or third-party ads integrated in code.
- No separate data collected for child accounts beyond the fields entered; code allows child accounts without email.
- Optional integrations: Home Assistant notify targets (if configured); other reminder channels not implemented.

## Key statements to include
- Data collection: limited to user-provided signup fields plus in-app activity data (chores, rewards, points, photos).
- Children’s data: child accounts can be created without email; no additional data is collected from children, but household admins control what they enter. Clarify responsibility for lawful creation/consent by admins/parents.
- No sale/sharing: data not sold; no third-party marketing/ads. Describe any processors (hosting, email, storage) if/when used.
- Security: password hashing (Django defaults), access limited to household members/admins; invite codes required to join households. Note pending API auth hardening if relevant.
- Data retention: stored while the household/account exists; describe deletion/retention policy (to be defined).
- Rights/requests: how to request deletion/export (email contact). Make clear there is no self-service portal yet.
- Media/uploads: photos are stored for verification; admins can remove them via normal app flows (if implemented) or by request.
- Cookies/sessions: Django session cookie for auth; no tracking cookies.
- International/hosting: specify hosting region once known; note if data stays within that region.
- Contact: provide email/contact form for privacy requests.

## TODO before publishing
- Confirm hosting location and any sub-processors (DB, object storage, email provider).
- Decide on retention timelines for accounts, households, and uploads.
- Add a process for data subject requests (export/delete) and document it.
- Review API/auth hardening status and update statements accordingly.
- Add links in footer to Privacy/Terms once the policy text is ready.
