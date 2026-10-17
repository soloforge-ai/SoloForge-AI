# P0-B4 Trusted QA Production Integration Preparation (NO DEPLOY)

## Current state
This PR adds an **unwired** server-side verification adapter, additive database
schema with an atomic claim RPC, and negative tests. No existing API/runtime
entrypoint imports the adapter. No production migration is applied.

## Trust boundary
- The `TrustedQABackend` is a protocol, NOT an implementation. Its implementer
  must authenticate the server caller, source immutable snapshots and current
  principal/grant state, enforce key custody and rotation, and fetch immutable
  input/output bytes from verified storage. Request bodies must never supply
  any trusted values.
- HMAC-SHA256 verification reuses P0-B3. Signing and verification share a
  secret; key rotation requires trusted key-id allowlists and lifecycle.
  **No production key issuer or key rotation implementation exists yet.**
- The adapter compares a signed envelope against an independent trusted
  snapshot, rechecks reviewer grant and both artifact byte hashes, then calls
  an injected atomic claim. It does not validate an entire route chain; it
  must not be treated as FINAL_QA authorization.
- `qa_claim_verified_evidence` checks current grant and inserts a unique
  replay claim plus audit in one transaction. It cannot independently verify
  a signature, artifact bytes, or authentication. The SQL function is
  service_role-only and cannot safely be exposed to untrusted clients.
- **Critical**: service_role has no direct DML and no grant/issuance RPC;
  provisioning is intentionally blocked pending an authenticated issuer.
  No live issuance is possible from this patch.
- Grant revocation and claim serialize on the same grant row. A claim that
  obtains the lock before revocation can commit first; revocation takes
  effect for subsequent claims, not retroactively.
- Audit entries created by claim/revoke are transactionally persisted.
  This is not yet an independently anchored tamper-evident audit log.
- Replay claim is irreversible; ambiguous outcomes require reconciliation.
  No automatic retry or provider execution is introduced.
- The adapter does not call `verify_revision_chain`, so route-wide evidence
  validation remains separate and is required before any future FINAL_QA use.

## Gates
P0-A `FINAL_QA` always returns `BLOCKED/TRUSTED_STAGE_CHAIN_MISSING`.
S1 generation and interactive chat always return False/HTTP 503.
No generation, publishing, worker, wallet, OAuth, provider, deployment,
production environment, or migration application is authorized.

## Next blocked items
Trusted issuer implementation, secure grant provisioning, actual backend
storage implementation, key lifecycle/rotation, full-chain server validation,
database concurrency tests against disposable PostgreSQL, and migration
rollout approval. Do NOT merge/deploy this PR without separate authorization.
