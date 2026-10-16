# P0-B4 — Trusted Identity, Key Custody and Atomic Claim Integration Design

Status: DESIGN ONLY / NOT WIRED / MERGE BLOCKED. Source reviewed at PR #188 HEAD e9fb18569d0894faa61109b7e725f534cac8a5d9. No deployment or production migration authorization.

## Verified existing infrastructure
- `backend/asset_forge/backend/soloforge_session.py`: Supabase bearer is validated by GET `/auth/v1/user` using the publishable key; requires the server-configured owner UUID, non-anonymous identity and GitHub in trusted app metadata. Short-lived v2 app sessions are HMAC-signed with `SOLOFORGE_SESSION_SECRET`. `SOLOFORGE_SESSION_NOT_BEFORE` supports mass revocation.
- `backend/asset_forge/backend/shared_supabase.py`: backend REST uses `SUPABASE_SECRET_KEY` from environment, not a per-user JWT. Service credential is database access, NOT proof of user authorization.
- `backend/asset_forge/backend/pollinations_oauth_router.py`: Pollinations OAuth sessions are provider credentials and cannot authorize QA or spending.
- `render.yaml`: `SUPABASE_URL` and `SUPABASE_SECRET_KEY` are marked `sync: false`; file does not establish the live Render secret values, rotation, or custody.
- `backend/asset_forge/backend/execution_policy.py`: generation and interactive chat return False.
- `supabase/migrations/202610160002_qa_atomic_chain_claim_preparation.sql`: owner-only, not executable by service_role, supports stage/order/grant/replay constraints, but does not verify cryptographic signatures or immutable artifact bytes.

## Target trust boundaries
1. **User to Backend:** Supabase Auth validates owner; app session authenticates owner requests. Validate job ownership and reviewer grants independently. Do not infer QA authorization from app session alone.
2. **Backend to Issuer:** issuer is a separately authenticated internal capability, never an HTTP-supplied `authenticated=true` or injected request mapping. Use short-lived workload identity with explicit audience/issuer and service allowlist; verify against a trusted identity provider. Default deny when no identity provider is provisioned.
3. **Issuer to Key Custody:** dedicated QA signing key, separate from `SOLOFORGE_SESSION_SECRET`, `SUPABASE_SECRET_KEY`, and Pollinations tokens. Key material must not be returned to a request. Prefer managed non-exportable signing with explicit key version, ACTIVE/VERIFY_ONLY/REVOKED lifecycle and rotation/revocation audit. Existing offline HMAC contracts are not proof of KMS custody.
4. **Verifier to Database:** after cryptographic and immutable-object verification, submit an authenticated, single-use server-issued verification receipt bound to ordered evidence IDs, job, revision, route, key versions and content hashes. Database must validate receipt provenance and expiry *inside* its transaction, lock grants, revision and snapshot rows in deterministic order, check key revocation, claim all IDs and write audit atomically. A pre-check followed by an unbound claim is vulnerable to TOCTOU.
5. **Immutable storage:** use versioned immutable references; reject mutable URLs, unversioned objects and client-supplied hash claims. Verify exact bytes and bind storage generation/version into the receipt. No upsert.

## Proposed minimal implementation sequence (future controlled-write work)
A. Implement server-only trusted principal resolver reusing `_supabase_owner_id` semantics without exposing user tokens or service secrets. Add deny-by-default tests for anonymous, non-owner, wrong provider, expired/forged app session and Pollinations-only session.
B. Choose and validate actual secret/signing provider capabilities, costs and key lifecycle before implementing a signing adapter. If non-exportable signing or trustworthy rotation is unavailable, keep the gate blocked; do not simulate KMS with an environment variable.
C. Build receipt issuance and verification with a durable nonce, authenticated issuer identity, key version and bounded expiry; avoid caller-provided proof maps. Introduce a dedicated DB role/capability with no general client access.
D. Add a new additive migration and disposable PostgreSQL tests for atomic full-chain claim, snapshot/revision mutation race, revocation race, replay, duplicate receipt, invalid signature and rollback. No production apply.
E. Wire the issuer, verifier and database adapter only after real integration tests pass. Keep `FINAL_QA`, generation, publishing and wallet execution locked pending separate owner approval.

## Outstanding decisions / blockers
- Select real workload identity and signing-key provider after verifying current Render/Supabase capabilities; no live provider settings or secrets were inspected in this read-only source audit.
- The existing QA SQL RPCs must not be exposed for live use as an authorization substitute.
- Never use the owner session HMAC secret as the QA signing key.
- Do not merge PR #188 until all four CI checks and dedicated real-identity/key-custody/transactional integration tests are successful and a separate merge approval is issued.
