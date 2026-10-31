# MVP Publora isolation and shared Pollinations OAuth

- External Publora publishing is intentionally disabled at both the publishing submission boundary and the shared Publora HTTP adapter. No environment variable enables it.
- Existing publishing database records, state transitions and code are preserved for future reconciliation; do not auto-retry uncertain submissions.
- Pollinations OAuth is already shared by Image Generation and Prawtwan Chat. No second OAuth connection is required for Prawtwan.
- **Important:** OAuth connection is not spending authorization. S1 keeps both image generation and Prawtwan provider calls locked until owner, wallet, approval and budget verification exists. This change does not unlock either feature.
- The MVP output path is local Save / Export. Any future Publora enablement requires separate owner approval, policy, tests and rollout.
- No Render configuration, worker enablement, production provider calls, merge or deployment is part of this change.

## Active-path detachment (2026-10-31)

- Content Job UI no longer offers Publora Publish Now or Schedule actions. Existing image Save / Export remains available.
- Embedded and dedicated worker startup no longer schedules the Publora publishing worker.
- Existing publishing endpoints and shared adapter remain fail-closed (HTTP 503) for compatibility; no external submission is enabled.
- Historical publish metadata, statuses, database records, and integration code remain unchanged. `READY_TO_PUBLISH` remains a persisted compatibility status; it is not a publishing authorization.
- This change is source-only pending review and merge; it does not prove production export E2E.
