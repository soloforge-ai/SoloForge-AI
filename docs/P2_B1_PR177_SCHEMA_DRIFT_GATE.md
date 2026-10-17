# P2-B1 Phase 1 source-of-truth drift gate (2026-10-14)

Status: **BLOCKED / NO-GO**. This document compares the recovered local original `20261009232734_generation_db_foundation_phase1.sql` (293 lines) and its reconciliation report against PR #177's `202610140001`–`004` migrations. It does not claim native PostgreSQL validation.

## Original Phase 1 invariants missing from PR #177

1. Wallet owner binding: `auth.users(id)` FK, `pollinations_sessions(session_id)` FK, wallet fingerprint SHA-256, QUEST/PAID category, `OAUTH_OWNER`, attestation timestamp, immutable binding, composite owner/session FKs. Current `provider_subject` text plus owner UUID is not sufficient proof.
2. Dedicated wallet allocation: `UNALLOCATED` zero default, verified allocation reference/timestamp, immutable binding and explicit state transitions. PR #177's `enabled` boolean can be set by a privileged DB writer without provider attestation.
3. Immutable approved snapshot: `content_job_id`, job revision, exact skill/version, snapshot digest, reference snapshot, 4-slide cardinality, quote version/expiry, approval revocation and composite snapshot FKs.
4. Request and asset contract: ordinals 1–4, immutable request snapshot, output bucket/object/version/SHA-256, unique immutable storage references, CALL_STARTED irreversible.
5. Security: FORCE ROW LEVEL SECURITY, append-only ledger/events, narrowly scoped service_role DML, private SECURITY INVOKER trigger helpers, immutable key/snapshot guards. PR #177 grants broad table DML to service_role and does not implement these guards.
6. Reconciliation: PR #177's settlement RPC relies on caller-supplied `p_actual` and `p_evidence` without trusted provider verification. Its `generation_record_result` has no controlled CALL_STARTED transition. No external execution is authorized.
7. Concurrency: `tests/p2b1/test_generation_db.py` still has a placeholder xfail; `test_generation_concurrency.py` requires an isolated native PostgreSQL/Supabase fixture. No native multi-connection test results exist.

## Safety gate

Do not merge, deploy, enable workers, call providers, or use production Supabase as a disposable test database. Do not apply both divergent generation schema families to the same database. Choose a reviewed replacement migration strategy and rework RPCs against the original composite-key contract; then run fresh native multi-connection tests in an isolated environment. Existing PR #177 is a draft work-in-progress, not production-ready.

## Environment inspection

Current execution container: no `postgres`, `initdb`, `psql`, `docker`, or `psycopg`; no verified disposable PostgreSQL DSN. Historical PGlite 177/177 does not establish native concurrency. No production DB mutation performed.
