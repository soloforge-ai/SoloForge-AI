# Manual Owner QA — Database Foundation (Draft; inert)

## Objective
Allow a future **explicit owner-triggered, single-image QA** to use an independently verified Pollinations OAuth wallet without enabling production workers. This PR is a database foundation only: **no API endpoint, no provider call, no allocation provisioning, no automatic worker, no deploy**.

## Verified baseline
- Production Supabase public schema has `pollinations_sessions` but no generation/wallet/budget tables (read-only inspection, 2026-10-18).
- Existing OAuth session has access token, expiry, scope; it does **not** prove SoloForge principal-to-wallet binding.
- `backend/asset_forge/main.py::_generate_sheet` uses a user's OAuth access token, but `require_generation_execution()` deliberately denies execution.
- `backend/asset_forge/backend/asset_provider.py` uses `POLLINATIONS_API_KEY`, so it is **not** the owner-wallet path.
- `backend/asset_forge/backend/execution_policy.py` stays untouched and deny-by-default.

## Database contract
One `manual_qa_allocations` row defines a verified owner, opaque wallet binding reference, pinned provider model, explicit Pollen-equivalent budget units and expiry. Allocation provisioning is **intentionally absent**: a later reviewed trusted backend must independently establish owner identity, wallet identity, provider-enforced spending limits, and explicit consent before creating a row. An allocation is not proof of these facts by itself.

`manual_qa_claim` is a service-role-only, atomic allocation lock + reservation + idempotency-key claim. The **only** response permitting one dispatch is `should_dispatch=true`; the backend must not dispatch if the transaction fails or returns false. Never retry a request after the provider call may have started. Identical idempotency keys return `false`, conflicting payloads fail.

`manual_qa_settle` records a known successful cost and releases unused reservation; uncertain results retain the full reservation under `RECONCILIATION_REQUIRED`. Reconciliation and allocation release require a separately reviewed, trusted manual process; no auto-retry or auto-release.

Both RPCs reject non-service-role calls. Tables have RLS enabled, no client DML grants, and no `SECURITY DEFINER` function accepts a client-supplied owner identity. Service-role access is privileged and must remain server-side.

## Before any provider QA is authorized
1. Verify backend SoloForge owner principal and independently bind the Pollinations provider account/wallet. Do not trust a client-provided owner ID or bearer token alone.
2. Verify provider budget/model restriction semantics (OAuth `budget` and `models` URL parameters alone are not enforcement evidence); obtain a dedicated wallet allocation and verify balance/cap.
3. Integrate a narrow **manual-only** endpoint with this claim RPC, and the existing OAuth-token image adapter, without changing the global S1 generation gate or enabling workers. No API-key fallback.
4. Add disposable PostgreSQL multi-connection tests: duplicate claim, different-key budget contention, tampered hash/model, anon/authenticated denial, expired/revoked allocation, ambiguous settlement and replay.
5. Add a provider spy test verifying **zero** calls on denial, **at most one** on a successful claim, and no retry on timeout; visual Thai glyph QA is a separate acceptance check.
6. Reconcile migration history and test on disposable Postgres **before** considering deployment. No direct application to production from this PR.

## Known limitations / safety notes
- This migration is inert until separately deployed and explicitly provisioned; it does not enable Manual QA by itself.
- Budget numbers are allocation units; real Pollen debits must be reconciled against authoritative provider usage. A trusted successful-cost report is required to settle.
- A server crash after claim and before dispatch leaves a reservation held; fail closed and reconcile.
- No external provider call or real QA image is made by this PR.
- Production workers, Publora, S1 execution policy, and existing content pipeline are unchanged.

## Scope
Exactly one additive migration and this contract. No P2-B1 Phase 1/2 migration cherry-pick, no RPCs for general generation, no new credentials, no deployment.
