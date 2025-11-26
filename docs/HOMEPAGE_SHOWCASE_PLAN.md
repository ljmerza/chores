# Home Page Showcase Plan

A structured outline for a marketing-style home/landing page that introduces Chore Manager, highlights the value props, and nudges visitors to create a household or join with an invite code. Replace the image placeholders with actual assets later.

## Goals and Audience
- Audience: families/roommates, household admins/parents, and invited members deciding whether to join.
- Goals: convey what the app does, reassure on safety/controls, showcase gamified chores/rewards, and create clear paths to start (create household) or join (invite code).

## Page Flow (Sections)
1) **Hero**: Promise + primary CTA to start a household; secondary CTA to join with invite code. Light social proof strip.
2) **How It Works**: 3 quick steps (create household, assign/complete chores, redeem rewards).
3) **Highlights**: Cards for gamification, schedules/reminders, rewards/approvals, household roles.
4) **UI Preview**: Slider or stacked screenshots showing dashboard, chores list, rewards redemption.
5) **For Parents/Admins**: Controls, roles, audit trails; optional secondary CTA to view docs.
6) **For Members/Kids**: Simple chores, streaks, points to rewards; mobile-friendly.
7) **Integrations & Automation**: Home Assistant hook, notifications; coming soon items.
8) **Testimonials/Quotes**: Short blurbs from demo users (replace with real).
9) **FAQ**: Top 4–6 questions on setup, invites, security, and costs.
10) **Final CTA**: Create household or join with invite code.

## Content Skeleton
- **Hero headline**: “Run your household like a team—chores, points, and rewards in one place.”
- **Subhead**: Emphasize multi-household support, roles (admin/member/child), and quick setup.
- **Primary CTA**: “Create a household” (links to signup create household).
- **Secondary CTA**: “Join with invite code” (links to invite flow).
- **Value bullets** (hero): “Chores with points and streaks”, “Photo verification”, “Rewards with approvals”.

## Visual Placeholders (swap with real assets)
- `[[IMG_HERO_ILLUSTRATION]]` – abstract illustration or blurred UI montage behind hero.
- `[[IMG_DASHBOARD_SCREENSHOT]]` – main dashboard view with points, leaderboard, active chores.
- `[[IMG_CHORE_FLOW]]` – step-by-step on claiming/completing a chore (mobile frame).
- `[[IMG_REWARDS_SCREENSHOT]]` – rewards catalog and redemption flow.
- `[[IMG_REMINDERS]]` – notification/reminder concept (email/push/Home Assistant badge).
- `[[IMG_TESTIMONIALS_BG]]` – subtle pattern or household photo behind testimonials.

## Layout Notes
- Keep a single-column mobile-first flow; introduce two-column splits on desktop for hero and highlight rows.
- Use CTA buttons in every major section (hero, highlights, admin/kid sections, final CTA).
- Stagger feature cards for depth; use light gradients or soft patterns instead of flat backgrounds.
- Keep copy tight; each section should stand alone with a short header + 1–3 bullets.

## Copy Blocks (draft)
- **Highlights**:
  - Gamified chores: points, streaks, leaderboards, transfers.
  - Schedules: recurring chores, due dates, photo verification.
  - Rewards: stock, approvals, per-user limits, audit trail.
  - Roles: admins/members/kids with invite codes and join flow.
- **Admin/Parent**: “Set roles, approve redemptions, see audit trails, and keep at least one admin on every household.”
- **Members/Kids**: “Claim chores, keep streaks alive, and redeem rewards with clear progress.”
- **Integrations**: “Home Assistant notify supported; email/SMS/push planned.”

## FAQ Starters
- Do I need my own server? (Docker/local supported; replace secret key before production.)
- Can I join an existing household? (Yes, via invite code verification flow.)
- Is there API auth? (Not yet—admin-only deployments advised; see auth hardening plan.)
- How do rewards approvals work? (Pending/approved/denied/fulfilled with audit fields.)
- What about reminders? (Celery/Redis wired; email/SMS/push stubs pending.)

## CTA Targets
- Primary: `/signup/create-household/`
- Secondary: `/invite/` (invite code entry)
- Optional tertiary: docs link for admins evaluating the app.

## Next Steps
- Replace placeholders with real screenshots from the current UI.
- Write final copy tone to match brand voice; keep under ~120 words per major section.
- Add analytics/tracking and A/B test CTAs once deployed.
