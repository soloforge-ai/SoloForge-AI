# Owner Identity V2 — local backend implementation

Status: backend and opt-in frontend/API integration implemented locally; not migrated, seeded, deployed or enabled.
Source baseline: `bfccddf219e71e46cd3b35b252e2a0ee6d022077`.
Owner decision baseline: 24 October 2026, Bootstrap Once → Verify on Login.

## Boundaries and reuse

The V2 registry is a new authority. The only reused runtime component is
`shared_supabase.supabase_request`, a transport rather than an identity authority.
No legacy tables, provider bindings, Auth users, trusted-binding configuration,
legacy signing keys or sessions participate in V2 authentication. No runtime
dependencies were added. Existing login, workers, generation, wallet/budget and
publishing controls are unchanged. The shared API guard accepts V2 bearers only after current registry/session validation.
Legacy signed tokens remain supported during transition; V2 rejection never falls back
to legacy identity or exchanges a V2 bearer for a legacy token.

All 10 source SQL files and Python V2 name references were inspected for name
collisions. No matching V2 tables/functions were found in this source snapshot.
Live database metadata was not inspected. The migration uses `CREATE`, not
`CREATE OR REPLACE` or `IF NOT EXISTS`: an unexpected live collision fails the
transaction instead of silently adopting or replacing another identity system.

## Files

| File | Responsibility |
| --- | --- |
| `backend/asset_forge/backend/owner_v2.py` | V2 service, opaque proof/session handling and SMTP/TLS delivery |
| `backend/asset_forge/backend/owner_v2_router.py` | Separate `/auth/owner-v2` HTTP endpoints |
| `backend/asset_forge/main.py` | Import and mount the new router only |
| `supabase/migrations/20261024151629_owner_identity_v2.sql` | Registry, provider references, challenges, sessions, permissions and atomic RPCs |
| `backend/asset_forge/tests/test_owner_v2.py` | HTTP/service/SQL security and compatibility tests |
| `backend/asset_forge/tests/owner_v2_pg_bridge.mjs` | Disposable, in-memory PostgreSQL test bridge |
| `backend/asset_forge/tests/run_owner_v2_offline.py` | Credential clearing and inherited Linux seccomp network denial |

## Registry and bootstrap

`soloforge_owners` permits exactly one owner. UUID, primary email and creation time
are immutable; no FK points to a legacy identity table. Creation time is the actual
V2 insertion time. `soloforge_owner_accounts` stores independent provider account
identifiers for Supabase, Render and Pollinations. Missing identifiers remain NULL
and pending. No account identifiers or emails are inferred from API keys, app IDs,
redirect URLs or other providers' records. Provider records are not queried on login.

The migration contains **no seed data**. A database administrator can later invoke
`owner_v2_bootstrap(uuid, email, accounts_json)` with separately confirmed values.
The API/backend service role cannot invoke it, insert an owner, or change owner
identity. Identical bootstrap UUID/email is a no-op, and a conflicting seed fails.
Optional account JSON accepts only `provider_account_id` and `account_email` for
the three named providers. All initial records are pending even when IDs are known.
Marking an account verified requires an account ID, evidence and verified timestamp
through a separately authorized administrator operation.

RLS is enabled on all four tables. PUBLIC, anon and authenticated have no table or
function privileges. Runtime RPCs are SECURITY INVOKER with an empty search path,
qualified relations and execute permission only for service_role. Runtime grants
allow owner/account reads, monotonic epoch updates/row locking and challenge/session
operations; no identity writes or bootstrap. Supabase's service secret remains a
privileged backend credential and must never reach the browser.

## Passwordless flow

1. `POST /auth/owner-v2/request` with `{"email":"owner@example.test"}`.
   The caller receives a challenge UUID and a 256-bit browser proof. Keep both only
   in the initiating client. A registered active owner receives a separate 256-bit
   one-time code by email. This is a pasteable **43-character code**, not a short
   numeric OTP. The trade-off avoids a new hashing/signing secret and offline
   brute-force exposure if the challenge table is disclosed.
2. `POST /auth/owner-v2/verify` with `challenge_id`, `browser_proof`, and `code`.
   SQL atomically validates delivery, owner status/epoch, expiry, both proof hashes,
   and attempts; it consumes the challenge and inserts one session in the same
   transaction. Only then does the backend return an `sf_owner_v2_` bearer token.
3. `GET /auth/owner-v2/session` with that bearer token checks the registry and
   session on every request, including current status, epoch, revocation and expiry.
4. `POST /auth/owner-v2/logout` with the bearer token revokes it. No refresh endpoint:
   reauthenticate by email after expiration. No authentication cookies are set.

Codes expire after 10 minutes, sessions after 1 hour. SQL owns the clock. Requested
`expires_in` values are upper bounds; delivery time reduces remaining lifetime.
Five failed redemption attempts exhaust a challenge. Email requests are limited
globally for the single owner to one per 60 seconds and five per hour, including
failed deliveries. A known-email attacker can exhaust that quota; ingress abuse
controls/CAPTCHA are a deployment consideration, not implemented here.

Wrong email, absent/disabled registry and rate-limited requests return the same 202
response shape and send no email. This does not claim constant-time enumeration
resistance: successful requests perform SMTP delivery. Infra failure is a sanitized
503. Wrong/expired/replayed/revoked proofs return 401. Success and handled error
responses use `Cache-Control: no-store`. Never log request bodies or bearer tokens
at the reverse proxy. The frontend must not place codes/tokens in URLs or persist
them in browser localStorage without an explicit security design.

Only SHA256 digests of high-entropy codes, browser proofs and session tokens are
stored. No custom session signing key is needed. Disabling or re-enabling an owner
increments the epoch, so old sessions and challenges cannot revive. An authorized
administrator can increment `auth_epoch` for revoke-all. Current-session logout is
the only public revocation endpoint.

SMTP failures leave a pending, unusable challenge. SMTP sends and state-changing
RPCs are never automatically retried. If SQL commits but its response is lost, a
session may exist whose token was not returned; the old challenge remains consumed.
It expires without granting access and the owner must request a fresh code later.

## Configuration — future authorized activation only

Default `OWNER_V2_AUTH_ENABLED` is absent/OFF; only the literal `true` (case-insensitive,
trimmed) enables the service. Enabling it is a separate production decision. Required:

- Existing non-identity transport: `SUPABASE_URL`, server-only `SUPABASE_SECRET_KEY`.
- V2 delivery: `OWNER_V2_SMTP_HOST`, `OWNER_V2_SMTP_USERNAME`,
  `OWNER_V2_SMTP_PASSWORD`, `OWNER_V2_SMTP_FROM`.
- Optional `OWNER_V2_SMTP_PORT` (default 465), using implicit TLS with certificate and
  hostname verification. No plaintext or opportunistic TLS fallback.

No provider or SMTP account was provisioned. No mail was sent. No Render variables
were read or changed. UUID/email remain unseeded until confirmed independently.
`SOLOFORGE_OWNER_USER_ID` may be an owner-confirmed seed, never authentication proof.
Legacy session variables, worker variables and undecided API keys remain untouched.
Login authorizes no wallet, billable provider call, generation or publishing action.

## Reproduce offline verification

On Linux, install test-only tooling outside the repository **before** isolation:

```bash
python3 -m venv ../owner-v2-test-venv
../owner-v2-test-venv/bin/pip install -r backend/asset_forge/requirements.txt pytest==8.3.5 httpx==0.28.1
npm install --prefix ../owner-v2-sql-test --no-audit --no-fund @electric-sql/pglite@0.3.14
```

Run from the repository root; set an absolute path to the installed module:

```bash
PYTHONPATH=backend/asset_forge:. \
OWNER_V2_TEST_PGLITE="$(realpath ../owner-v2-sql-test/node_modules/@electric-sql/pglite/dist/index.js)" \
../owner-v2-test-venv/bin/python backend/asset_forge/tests/run_owner_v2_offline.py \
  backend/asset_forge/tests/test_soloforge_session.py \
  backend/asset_forge/tests/test_shared_supabase.py \
  backend/asset_forge/tests/test_execution_policy.py
```

The runner clears application credentials, rejects inherited sockets, installs
seccomp denial for socket/connect/accept/io_uring and probes IPv4/IPv6 TCP/UDP denial.
It refuses to run without that protection. Descendants inherit the filter. Local
socketpair is allowed for TestClient; no listening HTTP or PostgreSQL server starts.
PGlite executes the actual migration and RPCs in memory. Delivery is a fake mailbox;
the REST transport is replaced with SQL calls to that disposable DB. Existing
regression tests use their own mocks. No real workers/providers are invoked.

Limitations: PGlite's bridge serializes queries; parallel redemption tests prove
single-consumption across repeated requests but not native PostgreSQL multi-connection
lock contention. Supabase/PostgREST grants and RPC mapping need staging verification,
as do live SMTP deliverability, ingress limits, device/browser E2E and production cutover.
Do not infer production readiness from offline results. Existing FastAPI lifecycle
and Starlette/httpx deprecation warnings are recorded, not repaired in this patch.

## Authorization boundary

This work permits local edits, branch creation and isolated tests only. No commit,
push, PR, merge, deploy, production/DB mutation, worker enablement or live provider
execution was authorized. Review this patch before any subsequent action. The
decision document's older read-only gate is superseded only for this explicitly
requested local implementation; it remains in force for production activation.

## Local frontend/API integration (current main baseline)

Baseline: `36621e15e0eab19de72ae8d5a7b679299421ead7` (merged backend).
The opt-in Flutter build define `SOLOFORGE_OWNER_V2=true` selects the independent
email/code login and shared memory-only session service. Default builds retain
the GitHub gate. `SOLOFORGE_OWNER_OAUTH_UAT` remains legacy identity-only UAT.
V2 builds skip Supabase Auth initialization unless explicitly running that UAT.
No production/build configuration was enabled by this patch.

The login UI requests a code, presents a generic delivery message, verifies the
full 43-character code, and unlocks Home. Proofs are discarded before redemption;
ambiguous failures require a fresh request and are never retried automatically.
Tokens are shared only within the app process, never persisted or placed in URLs.
Restart requires email login again. Session validation runs before content API
requests and on app resume; a local one-hour timer also removes stale UI access.
Logout removes local access immediately and calls server revocation once. If the
response is lost, the UI reports that revocation is unconfirmed; there is no retry.

The existing content service reuses `SoloForgeSessionService.authorizationHeaders`;
in V2 builds it delegates to the V2 service, without GitHub bootstrap fallback.
The backend shared guard independently validates every protected request against
V2 session status/expiry/revocation/owner epoch. V2 bearer tokens are rejected before
legacy bootstrap/refresh can forward them to Supabase Auth. Existing execution,
wallet/budget, provider, and publishing policy remains independently enforced.
Neither authentication nor this UI grants execution/spending consent.

Local validation uses the existing seccomp runner and actual in-memory migration/RPCs,
plus frontend MockClient/widget tests. Live PostgREST, native multi-connection SQL,
SMTP and production/device cutover remain separate verification steps.
