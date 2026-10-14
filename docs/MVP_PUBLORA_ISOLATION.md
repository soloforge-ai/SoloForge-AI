# MVP Publora isolation and shared Pollinations OAuth

- External Publora publishing is intentionally disabled at both the publishing submission boundary and the shared Publora HTTP adapter. No environment variable enables it.
- Existing publishing database records, state transitions and code are preserved for future reconciliation; do not auto-retry uncertain submissions.
- Pollinations OAuth is already shared by Image Generation and Prawtwan Chat. No second OAuth connection is required for Prawtwan.
- **Important:** OAuth connection is not spending authorization. S1 keeps both image generation and Prawtwan provider calls locked until owner, wallet, approval and budget verification exists. This change does not unlock either feature.
- The MVP output path is local Save / Export. Any future Publora enablement requires separate owner approval, policy, tests and rollout.
- No Render configuration, worker enablement, production provider calls, merge or deployment is part of this change.
