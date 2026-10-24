# Combined Manual Owner QA — Disposable PostgreSQL Integration

Pinned sources:
- PR #179 `56bd2019c95b0008166fcc346f0118a57c548753`: owner-binding SQL (unchanged)
- PR #192 `913f60c1794f794db77dbbb821cd1878b8f57c93`: QA SQL and original PostgreSQL tests (unchanged)
- Base main `2e1f6db308776e0bdb306bbfacf5b5f9a7ed2fe2`

The PR runs **pull_request CI only** with a synthetic PostgreSQL 16 database. No production credentials, API keys, provider network calls, OAuth exchanges, deployments, or workers.

Coverage: both migrations together, legacy ownerless session retention, rejection of new unbound/partial sessions, bound insert, service RPC existence and client EXECUTE denial, plus original PR #192 concurrency/RLS/idempotency/settlement tests.

Not covered: runtime OAuth router, real wallet ownership or spending authorization, allocation provisioning, provider dispatch, live execution. Metadata verification is NOT spending authorization. These remain blocked/fail-closed; do not infer live readiness from green CI.

This is the **G1/G2 foundation of the approved Integration Blueprint**, not a claim of full end-to-end integration.
