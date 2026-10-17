# P0-B4 follow-up: Trusted Issuer / Key Lifecycle / Full Chain

Additional **unwired** pure Python contracts in `trusted_qa_issuer.py`:
- `issue_trusted` loads a server-authoritative envelope, principal, current grant,
  review target, UTC evaluation time and immutable input/output bytes. It
  re-hashes both before signing with a trusted key returned by an injected
  issuer authority. It is not an authenticated server implementation.
- `verify_with_lifecycle` accepts only trusted key records with ACTIVE or
  VERIFY_ONLY status and bounded UTC validity. REVOKED, unknown and expired
  keys are blocked. The underlying HMAC uses shared secrets, and the
  implementation does not provision, store, rotate or revoke keys in a KMS.
- `verify_trusted_chain` checks the exact IMAGE/VIDEO graph, each signature,
  current reviewer authorization, immutable input/output hashes, authoritative
  revisions, ordered dependencies and read-only consumed IDs. Its PASS remains
  advisory: no atomic claim is performed for the entire chain.

**Remaining critical gates:** no production authority implementation, no
key custody/rotation service, no secure grant/evidence provisioning, no
transactional all-stage chain claim or atomic full-chain audit, and no runtime
integration. A server must NOT use these fixture-driven protocols to authorize
FINAL_QA, generation, publishing or spending. The existing SQL per-evidence
claim RPC remains independent and does not establish whole-chain atomicity.
No migration application, deploy or production changes in this PR.
