# Pollinations SK Lifecycle — Owner-Approved Decision (2026-10-26)

Status: **Design approved; implementation and verification pending.** This document does not authorize deployment, provider generation, or spending.

## Outcome

Reuse an existing owner-authorized Pollinations scoped `sk_` credential whenever it remains valid, rather than issuing a new key on every SoloForge login. Keep Owner V2 identity, Pollinations provider identity, and spending authorization separate.

## Verified baseline

- Base main: `4bc9f8a179836fb04c4300a5c93ccb7c7ff6228c`.
- Existing code: `backend/asset_forge/backend/pollinations_oauth_router.py`, `backend/asset_forge/backend/pollinations_oauth.py`, `frontend/lib/services/pollinations_session_service.dart`.
- The OAuth authorization-code + PKCE flow already receives an `sk_`-prefixed bearer credential, stores it in `public.pollinations_sessions`, and exchanges a one-time mobile handoff.
- Production observation on 2026-10-26: callback 302, mobile exchange 200, status 200; a corresponding Supabase session exists with expiry 2026-10-29. This confirms session persistence, **not** key ownership, revocation, or remaining per-key budget.
- `public.soloforge_owner_accounts` has a Pollinations row with `verification_status=pending` and no verified `provider_account_id`. Never auto-bind the first provider subject to the owner.
- Existing `pollinations_sessions` stores `access_token` and `expires_at`; existing login initiates OAuth rather than a provider-key lifecycle preflight.

## Required minimal implementation

1. After authenticated Owner V2 login, query only owner-authorized, already-verified Pollinations bindings and their existing sessions. Never select an arbitrary session merely because it exists.
2. Before starting a new OAuth authorization, perform a server-side, read-only preflight for the existing key. Validate expiration, provider acceptance/revocation, provider `sub`, and available key-specific budget if supported by documented provider endpoints. Distinguish account pollen balance from delegated key budget. Do not infer provider guarantees from a local timestamp or HTTP 200 alone.
3. Verify provider `sub` by exact comparison against an independently owner-authorized provider account ID. The proposed expected ID is `PxBt6HZT1MCQh4Bmf1iTfE7XP8oLrSCX`; its origin and authorization must be independently verified before treating it as trusted. Do not rely on display name or email.
4. After OAuth token exchange, validate the credential, retrieve provider identity server-side, enforce owner authorization, then persist only verified binding metadata and the credential in protected server-side storage. No token or full userinfo payload in logs, URLs, UI, or Git.
5. Fail closed on invalid credentials, subject mismatch, provider errors, unknown budget, missing owner authorization, or persistence errors. Do not issue a usable mobile session or mark a binding verified on failure.
6. Return explicit lifecycle states: `VALID`, `EXPIRED`, `REVOKED`, `BUDGET_EXHAUSTED`, `ACCOUNT_BALANCE_EXHAUSTED`, `UNKNOWN`. Only emit a definitive state when provider evidence supports it; otherwise `UNKNOWN`.
7. Reuse `VALID` key. For any other state, show a clear explanation and require explicit owner approval before starting OAuth to issue a replacement key. Never auto-create or auto-renew keys. Never treat OAuth login as wallet spending consent.
8. Preserve existing fail-closed workers/publishing/generation controls. No API-key fallback and no generation call as a health check.

## Acceptance criteria / offline tests

- Existing verified key remains usable across repeated Owner V2 logins without creating another key.
- Exact matching `sub` + authorized owner succeeds; wrong/missing `sub`, wrong owner, unverified binding, revoked/expired credential, provider timeout, unknown budget, and DB error fail closed.
- Preflight is read-only and does not invoke token issuance or any generation endpoint.
- Explicit owner confirmation is required for replacement; concurrency/idempotency prevents duplicate replacement attempts.
- No secret values in logs or test output; no unapproved production mutation.
- Tests must mock Pollinations and Supabase. Record actual commands and results; do not claim production E2E without a separate authorized deployment and verification.

## Explicit exclusions

No automatic key creation, production database migration, production deployment, workers, publishing, billable provider generation, or merge under this decision note. Implementation must separately establish exact provider endpoints and owner authorization before enabling lifecycle transitions.
