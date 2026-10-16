# P0-B3.1 Offline Reviewer Authorization Contract

**Status:** offline-only policy fixture; NOT an authenticated issuer or production authorization gate.

`authorize_reviewer(trusted_principal, trusted_grant, trusted_target, evaluated_at)` is a pure function returning `PASS` or `BLOCKED`.

All four arguments must be independently server-derived in a future approved integration. They are **fixtures only** in P0-B3.1. Never derive a trusted principal, grant, target or evaluation clock from submitted QA evidence, an arbitrary caller-supplied `reviewer_id`, a provider wallet, or an unverified token.

- `trusted_principal`: exact keys `principal_id`, `authenticated` (boolean true only), `session_expires_at` (UTC Z).
- `trusted_grant`: exact keys `principal_id`, `job_id`, `allowed_stages` (nonempty unique stage list), `revision_id`, `expires_at` (UTC Z), `revoked` (boolean false only).
- `trusted_target`: exact keys `job_id`, `stage`, `revision_id`.
- `evaluated_at`: trusted UTC Z timestamp; equality with either expiry is denied.

Authorization is restricted to exact principal, job, stage and revision matches. Unknown stages, extra fields, malformed timestamps, expired or revoked grants, and unauthenticated principals fail closed. No evidence is signed, issued, persisted, or cryptographically verified. No new roles, OAuth flows, APIs, database migrations, or provider calls are introduced.

**Important limitation:** If an attacker can control both the supposed trusted principal and grant, the policy cannot detect forgery. Authenticating those inputs, checking actual revocation and trusted time, and issuing signed evidence are future phases requiring separate approval.

P0-A `FINAL_QA` and S1 generation execution remain fail-closed; this policy's `PASS` must not be used to unlock either.
