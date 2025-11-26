# FAQ Planning Notes

Draft questions/answers for a future FAQ page. Tailor details once hosting, auth, and policies are finalized.

## Suggested Q&A
- **What is Chore Manager?** A multi-household chore and rewards app with roles (admin/member/child), points, streaks, and approvals.
- **How do I start?** Create a household as an admin or join with a verified invite code; add members and set chores/rewards.
- **Do you collect data?** Only the info you enter for accounts (username, name, email for admins/parents) plus in-app activity (chores, points, rewards, notifications, optional photos). No analytics/ads tracking in the code. Child accounts can be created without email; no extra data is collected for children beyond what admins enter.
- **Are child accounts private?** Admins/parents control child accounts. The system does not collect additional data from children; admins decide what to enter and should follow applicable consent rules.
- **Is there API access?** API auth isn’t implemented yet; all endpoints are currently open. Restrict deployments accordingly until auth is added.
- **How are reminders sent?** In-app notifications work; Home Assistant notify can be configured. Email/SMS/push are stubbed pending implementation.
- **How do rewards approvals work?** Rewards can require approval; redemptions move through pending/approved/denied/fulfilled/cancelled with audit fields.
- **Can I self-host?** Yes; Docker compose is provided. Replace default secrets and secure your deployment before exposing it.
- **Can I delete my data?** Data removal/export would be handled by request/admin action; define and document the process before launch.
- **Where is data stored?** Specify hosting region/provider once chosen; no third-party marketing trackers are in the code.

## TODO before publishing
- Confirm hosting region/providers and add to the relevant answers.
- Finalize data deletion/export process and update the FAQ.
- Update the API/auth answer when authentication is implemented.
- Link to Privacy and Terms pages from the FAQ once published.
