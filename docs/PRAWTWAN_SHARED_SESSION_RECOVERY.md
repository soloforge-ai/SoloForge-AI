# Prawtwan shared OAuth session recovery

## Scope and source snapshot

Owner-authorized controlled write: one new branch and one Draft PR; no changes to
PR #173/#174, no providers, production configuration, workers, migration or deployment.

- Main: `3611f73853915d6254c0f4c4427106fe3073fffd`.
- Draft #173: `db5c7289ca1e01df8280b5fe381bca80aa3296ca` (S1).
- Draft #174: `2747fbf8d4a110ad4ac37daf83c6ca3a11b21efc` (Publora disabled).
- Branch: `fix/prawtwan-shared-session-recovery`, based on #174.
- Target: `fix/mvp-disable-publora-shared-oauth`. The stack is intentional:
  this fix must not land without the S1 and Publora prerequisites.

Allowed scope: shared Flutter session service, Prawtwan copy and mocked regression
tests, backend Prawtwan contract tests and this evidence note. Authentication
lifecycle is security-sensitive; backend policies and production are excluded.

## Confirmed root causes at the base SHA

`frontend/lib/services/pollinations_session_service.dart`:

- `handleWebCallbackIfPresent` (lines 122–139) skipped a new handoff whenever
  *any* stored token existed, even when `status()` found it expired/invalid.
- `handleCallback` / `_exchangeHandoffCode` (110–168) had no coordination across
  the independent Home, Asset Forge and Prawtwan service instances. Each could
  consume the same one-time callback; native initial-link replay also retried it.
- `status` (170–190) deleted shared storage for every non-2xx response and invalid
  status, including temporary outages or a response for a token already replaced
  by another page's callback.
- `connect` (67–103) checked an existing session but did not share an in-flight
  login launch across instances.

These are code-confirmed failure paths, not a claim of live-device reproduction.
All three snapshots have the same affected frontend source. Home uses the shared
service (`frontend/lib/pages/home_page.dart`, `_loadPollinationsConnection`, 198–243),
Asset Forge uses it (`asset_forge_page.dart`, 80–145), and Prawtwan uses it
(`prawtwan_chat_page.dart`, 34–180). There is no need for a second provider login.

## Minimal change

Validate the current session before callback exchange; share login-launch and
one-time handoff futures across service instances; serialize token writes and
conditional invalidation so stale results cannot remove a newer token. Temporary
status errors retain the token but do not report a successful connection or
launch fresh OAuth. Duplicate completed callbacks consult current status instead
of trusting a cached success. Failed exchanges are not automatically retried.
The in-memory callback cache is bounded to 16 entries and is not durable or
cross-tab coordination; backend one-time handoff enforcement remains authoritative.

Correct Thai/English connection and lock copy: OAuth connects the shared session,
not wallet spending. S1 503 responses show the lock instead of suggesting
reconnection; 403 does not become a login instruction. The existing send flow
may contact the SoloForge backend; the backend denies remote provider execution.

The existing UI history, draft and language snapshot mechanism is retained:
`prawtwan_chat_page.dart`, `_connect` 149–180 / `_handleCallback` 119–146;
`prawtwan_oauth_return_web.dart`, `savePrawtwanReturn` / `takePrawtwanReturn` 17–56.
Native callbacks preserve in-memory page state; native process death and
cross-device/history persistence are not added or claimed.

## Authorization boundary and remaining prerequisites

Prawtwan -> shared session bearer -> backend `chat_with_prawtwan`
(`backend/asset_forge/backend/prawtwan_chat.py`, 81–95) -> real S1
`require_generation_execution` (`execution_policy.py`, 18–29) -> 503.
Missing/expired/forged/unrecognized bearer -> 401 before dispatch. Provider request
construction follows the execution gate. There is no API-key fallback added.

`_OAuthSession` (`pollinations_oauth_router.py`, 45–48) contains only provider token,
expiry and scope. It does **not** bind a SoloForge principal, prove wallet
ownership, reserve budget or authorize a charge. An unrecognized session is
rejected; a valid session belonging to another person cannot currently be
independently distinguished. S1 denial protects both cases.

Before remote chat can be enabled, independently verified principal/account/
wallet binding, explicit spending approval, provider-enforced billing limits or
allocation, per-request permission, atomic idempotency and safe handling of
ambiguous outcomes are required. OAuth success alone is insufficient.

Publora and owner-session checks inherited from #174 are unchanged. The publishing
regression suite exercises denial before DB/network operations. No environment
switch, worker startup or billable fallback is introduced.

## Validation

Tests use synthetic tokens and mocked HTTP only. Python runs with a sanitized
environment and an external runner denying socket connect/connect_ex/create_connection;
no production values are read. Existing adapter happy-path tests deliberately
substitute gates in isolated mocks; the new deny tests use the real session resolver
and real S1 policy, including repeated requests. Two new publishing regressions confirm a valid
Pollinations session cannot authorize publish-now/schedule as a SoloForge owner.

Python full suite: 342 passed, 60 deprecation warnings, zero outbound attempts.
Focused OAuth/Prawtwan/S1/Publora suite: 130 passed, 45 deprecation warnings,
zero outbound attempts. Initial full run: 339 passed / 1 failed in the new test;
fixed collection-order fixture isolation across repository/deployment import aliases,
without changing runtime or bypassing the resolver.

Flutter 3.47.0 / Dart 3.13.0: full suite 70 passed; focused OAuth/Prawtwan
suite 35 passed; final session-file rerun after lint fixes 13 passed.
`flutter analyze --no-pub`: no issues. Initial analyze found two missing-brace
lint infos in the new test, fixed without changing behavior.
Web snapshot check: compiled to JavaScript and executed with Node mocked
sessionStorage; eight assertions passed (not a real browser/device E2E).

SDK bootstrap initially hit a denied cloud metadata probe from Flutter's Azure
bot detector. Source inspection proved `CI=true` short-circuits that probe;
subsequent commands used CI mode with analytics disabled. A tar ownership error
was resolved with SDK-only `TAR_OPTIONS=--no-same-owner`. No credentials were read.
`flutter pub get` resolved existing declared constraints; generated platform,
analysis configuration and lockfile outputs were restored, not included in this PR.
No dependency changes are proposed. Exact commands are in the Draft PR description.
Live OAuth, provider execution, production restoration and deployment are NOT VERIFIED.
Human review is required before advancing this Draft PR or enabling remote chat.
