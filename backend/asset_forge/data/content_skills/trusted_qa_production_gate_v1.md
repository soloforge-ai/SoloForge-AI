# P0-B4 Production Trust Gate — explicit fail-closed boundary

This PR adds `trusted_qa_production_gate.py` as a **permanently denied
production authorization gate** until a separately approved, verifiable
integration is delivered. Passing offline verification or disposable PostgreSQL
tests is not sufficient to unlock FINAL_QA.

## Missing production prerequisites
1. Authenticated internal service identity, audience/issuer validation,
   non-forgeable server principal and authorization bound to job/revision.
2. Provider-backed key custody and rotation/revocation; the offline
   HMAC shared secret must not be passed through untrusted request contexts.
3. One transaction that locks reviewer grants, revision/snapshot state,
   verifies immutable artifact identities, enforces replay uniqueness and
   writes audit records atomically.
4. Integration tests against the chosen identity provider and key service,
   plus real PostgreSQL race tests including revocation and snapshot mutation.

**Critical caveat:** `qa_claim_verified_chain` only enforces relational
stage/order/revocation/replay rules. It does not validate signatures, KMS key
state, or immutable storage bytes. The RPC has no application EXECUTE grants
and MUST remain unavailable in production.

**No production auth/KMS implementation is claimed.** Deploy, migration
application, workers, generation and publishing remain unauthorized.
