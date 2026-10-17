# P2-B1 PR #177 — source-of-truth drift gate (2026-10-14)

**Status: BLOCKED / NO-GO.** This document records verified differences, not a passing migration or test result.

## Authoritative recovered source
- Local recovered Phase 1 file: `20261009232734_generation_db_foundation_phase1.sql` (293 lines).
- Original base: `d515a9452b4bfa67f905c7a1579b1bf525d0feca`.
- Reconciliation notes: `P2_B1_PHASE1_RECONCILIATION.md`.
- PGlite historical 177/177 does not establish native PostgreSQL concurrency.

## Incompatible contracts in PR #177
1. Original budget account uses `owner_user_id` FK to `auth.users`, `pollinations_session_id` FK to `pollinations_sessions(session_id)`, `provider_wallet_fingerprint`, `wallet_category`, `allocation_state` and attestation fields. PR #177 uses `provider_subject` and `enabled`; these are **not equivalent**. Original docs explicitly say even the FK is not proof of provider wallet ownership.
2. Original approvals bind `content_job_id`, `content_job_revision`, `skill_id='SALES_CAROUSEL_4_V1'`, digest, four slides, model/quote/reference snapshots. PR #177 does not enforce these.
3. Original requests use `slide_ordinal between 1 and 4`, output bucket/object/version/SHA256 and immutable references; PR #177 uses `slide_index >= 0`.
4. Original uses `generation_internal` immutable/snapshot triggers, FORCE RLS, no DELETE/TRUNCATE grants, narrow service-role UPDATE grants. PR #177 lacks these.
5. Original state vocabulary: `CLAIMED/CALL_STARTED/SUCCEEDED/FAILED_CONFIRMED/UNKNOWN_RECONCILE`; PR #177 uses incompatible `APPROVED/RUNNING/RECONCILIATION_REQUIRED` execution states.
6. Original ledger has execution-level `RESERVE/SETTLE/RELEASE_AFTER_VERIFICATION/MANUAL_ADJUST` with evidence; PR #177 uses request-level `RESERVE/SETTLE/RELEASE/ADJUST`. Settlement functions cannot be transplanted without a complete transaction design.

## Mandatory implementation sequence
1. Replace the **unapplied** PR #177 schema with the original Phase 1 contract as one consistent migration; remove/rewrite all dependent PR #177 RPCs and tests in the same controlled change. Do not stack duplicate CREATE TABLE migrations.
2. Provide isolated PostgreSQL bootstrap for `auth.users`, `content_jobs`, `pollinations_sessions` with synthetic rows. Never apply repository history blindly or run against production.
3. Implement service-only owner/session/wallet attestation, immutable approval, atomic aggregate reservation and claim, call-start fence, explicit settlement and ambiguous-result reconciliation; no provider calls.
4. Run migration from empty disposable DB, permission tests as anon/authenticated/service_role, 2+ independent PostgreSQL connections for oversubscription/idempotency, settlement replay and failure-injection tests.
5. Record exact command, engine version, SHA, and passing test output. Until then: NO-GO.

## Environment inspection
No `postgres`, `initdb`, `pg_ctl`, `psql`, or Docker binary found in the current runtime. Supabase project development branches previously returned empty. No disposable instance or native test run has been verified. A new Supabase branch requires separate cost confirmation; never create one without that approval.

**No merge, deployment, worker enabling, wallet debit, provider call, or production migration authorized.**
