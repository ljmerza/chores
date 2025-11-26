# Terms of Service Planning Notes

Draft outline for a future Terms of Service. Confirm details with legal counsel and update to match your actual deployment model (self-hosted vs. managed service).

## Scope and Offering
- Describe what Chore Manager is: multi-household chore/reward app with roles (admin/member/child), points, streaks, rewards, and optional integrations.
- Clarify whether you operate a hosted service or users self-host; note Docker compose setup and default insecure dev settings.
- Eligibility: accounts created by adults; admins/parents are responsible for creating child accounts and obtaining any necessary consent.

## Accounts and Access
- Account creation: username required; email required for admins/parents, optional for children. Household join requires invite code.
- Roles and permissions: admins can invite/remove members, adjust roles, regenerate invite codes, and approve rewards.
- Security expectations: users must keep credentials confidential; advise changing default secrets and securing hosts in production.
- API/auth: currently no API auth in code—production use should restrict access; document when/if API auth is added.

## User Content and Responsibilities
- Users control household data: chore entries, photos for verification, rewards, and notifications. Users must have rights to content they upload.
- Prohibited uses: unlawful content, abuse, attempts to bypass security, or unauthorized access to other households.
- Media: photo uploads for verification are stored; admins can manage/delete via app flows (if available) or by request.

## Privacy Reference
- Link to the Privacy Statement (planned separately) and summarize that data collected is limited to account fields and in-app activity; no ads/analytics in code.
- Children: no extra data collected for child accounts; admins/parents must create/oversee them lawfully.

## Availability, Changes, and Support
- Uptime/availability: no guarantees; clarify if best-effort support or community support only.
- Updates: describe how updates/changes are delivered (releases, Docker images) and how users are notified.
- Third-party services: call out optional integrations (e.g., Home Assistant notify) and any hosting/email/storage providers if used.

## Liability and Warranty
- Software provided “as is,” no warranties; limit liability to the extent permitted by law.
- Indemnity: users are responsible for their content and use.

## Termination and Data Handling
- Account/household removal: outline how accounts/households can be deleted; note retention policy once defined.
- Data exports: describe whether and how users can request data export.

## Contact
- Provide contact email/form for terms-related questions or notices.

## TODO before publishing
- Decide if you’re offering a hosted service or only self-host; align terms accordingly.
- Define support model, uptime stance, and any SLAs (if any).
- Confirm hosting region and subprocessors; update references.
- Add retention, deletion, and export mechanics to match privacy statement.
