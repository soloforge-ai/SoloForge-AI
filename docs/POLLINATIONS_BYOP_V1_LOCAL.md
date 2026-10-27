# BYOP V1 local application wiring — verification limited by sandbox

## Local role/readiness and Developer Earnings follow-up (2026-10-27)

Uncommitted follow-up based on `2f63dd570eb630958ea0a1169bc184412c96fac9`.
No push, PR update, deployment, migration or live provider/OAuth call is authorized
or performed in this follow-up. Earlier CI results below apply to that committed
baseline, not to these new local changes.

Owner V2 principals are eligible for a controlled pilot only. Active Members can
still connect/verify/disconnect and manage their own records, but production Flow
denies consent and execution before reservation; it checks the role again before
dispatch. Owner eligibility never replaces trusted pricing, consent, budget,
credential ownership or the existing hard execution lock. `/v1/byop/session`
now reports this distinction and Flutter disables member spending actions.

Trusted pricing must explicitly attest `includes_all_charges: true` before consent
or reservation, including reuse of an older RESERVED execution. The amount is a
maximum total inclusive of any applicable markup, not a base-only quote, confirmed
charge or earnings. Missing/old/base-only quotes fail closed and need fresh consent.
No provider price is invented; production pricing still returns 503. Flutter
displays the server-quoted maximum when available and otherwise reports unknown.

### Verified official provider contracts

Sources pinned to Pollinations revision
`5fe341f5690bb0c553c02ab77f35a9a762413fe3`, inspected 2026-10-27:

- [Connect User Wallets](https://github.com/pollinations/pollinations/blob/5fe341f5690bb0c553c02ab77f35a9a762413fe3/BRING_YOUR_OWN_POLLEN.md):
  publishable App Keys identify the OAuth client; PKCE issues a scoped user SK.
  Developer earnings are opt-in with `earningsEnabled`, add 25% over base usage,
  and credit the same Quest/Paid Pollen balance type used by the payer. OAuth
  approval does not replace SoloForge's per-execution consent. There are no refresh
  tokens; expired keys require reauthorization.
- [Provider markup code](https://github.com/pollinations/pollinations/blob/5fe341f5690bb0c553c02ab77f35a9a762413fe3/shared/billing/markup.ts):
  requires trusted `byop_client_key_id`, a valid/enabled publishable client,
  `earningsEnabled`, and different payer/app-owner subjects. **App-owner self-use
  does not earn developer markup.** A submitted personal SK does not establish
  these conditions; never add an invented generation attribution header.
- [App Lookup](https://github.com/pollinations/pollinations/blob/5fe341f5690bb0c553c02ab77f35a9a762413fe3/enter.pollinations.ai/src/routes/app-lookup.ts):
  resolves the client ID, app owner, registered redirects and earnings setting.
  Client identity is not inferred from a redirect hostname.
- [API docs](https://github.com/pollinations/pollinations/blob/5fe341f5690bb0c553c02ab77f35a9a762413fe3/APIDOCS.md)
  distinguish HTTP 402 account/key-budget exhaustion from HTTP 401 authentication.
  No automatic quest redirect contract was verified.
- [FAQ](https://github.com/pollinations/pollinations/blob/5fe341f5690bb0c553c02ab77f35a9a762413fe3/enter.pollinations.ai/POLLEN_FAQ.md)
  explicitly links `https://enter.pollinations.ai/quests`. UI offers this official
  destination as text; it never auto-navigates, claims a reward or retries a call.

`pollinations_app_contract.py` prepares only an **offline** attributed authorization
request using the existing PKCE URL builder and verified server-side App Lookup
evidence for the intended client/developer/redirect. It performs no I/O and is not
mounted as a new onboarding endpoint. Existing-SK readiness remains
`UNVERIFIED_EXISTING_SK`, earnings eligibility/confirmation false, amounts unknown.
No developer earnings ledger, wallet or alternate OAuth system was introduced.

### Remaining blockers and verification scope

Live earnings require a separately authorized App Key/OAuth onboarding integration
that durably binds provider-issued SKs to the verified client, independent app-owner
identity, current earnings setting and payer. Current records do not establish
that evidence. App configuration alone is not a confirmed credit. Model pricing,
key budget, native database/schema/Storage checks and charge/earnings reconciliation
remain blocked; no balance fetch, earnings claim or spending unlock is added.

The pre-existing owner/member lower-layer fixtures retain explicit future-member
policy injection to exercise tenant isolation. New tests separately use the real
default owner-only policy, including the actual application Flow construction and
two member HTTP denial cases. The latter are collected only locally; HTTP tests
must execute in a later authorized CI runtime. Flutter is unavailable locally.

Final bounded, credential-cleared, seccomp network-denied results for this patch:
**78 PASS** (BYOP component/repository/App Key contract suites, 22.63s), plus
**19 PASS** (selected non-HTTP execution-policy/security regressions, 0.42s).
No skip/deselection in these explicitly selected runs; three deprecation warnings
per run. Six HTTP cases collect (0.27s), **NOT RUN**. Flutter analyzer/tests/build,
including the new readiness service test, **NOT RUN** (SDK absent). Python AST,
runtime imports/OpenAPI, and `git diff --check` are checked separately. The earlier
737 backend / 105 Flutter CI passes are not evidence for this uncommitted patch.

Changed files in this follow-up (relative to the committed delivery):

- `backend/asset_forge/backend/byop_principal.py`
- `backend/asset_forge/backend/byop_flow.py`
- `backend/asset_forge/backend/byop_ledger.py`
- `backend/asset_forge/backend/byop_router.py`
- `backend/asset_forge/backend/pollinations_app_contract.py` (new)
- `backend/asset_forge/tests/test_byop_repository.py`
- `backend/asset_forge/tests/test_byop_v1.py`
- `backend/asset_forge/tests/test_byop_http.py`
- `backend/asset_forge/tests/test_pollinations_app_contract.py` (new)
- `frontend/lib/services/byop_service.dart`
- `frontend/lib/pages/byop_page.dart`
- `frontend/test/byop_service_test.dart`
- `docs/POLLINATIONS_BYOP_V1_LOCAL.md`

The following sections describe the preserved earlier delivery and its history.

Delivery branch: `feature/pollinations-byop-v1`; original worktree remains untouched.
Integration base: `4bc9f8a179836fb04c4300a5c93ccb7c7ff6228c`.
Draft delivery: https://github.com/soloforge-ai/SoloForge-AI/pull/212
Initial delivered head: `474ac1ff1ffa8fb0dd75731b15f1b170510a2664`.
Its tree `6ff5f1104934d0e7c6912f714182b3d6f0cb2d4d` exactly matches the original
51-file reviewed local commit, preserved at `local/pollinations-byop-v1-delivery-checkpoint`.
Sources reconstructed from GitHub blobs and validated patches:

- #210: `97bececac53a5e16c4d14cb284862b5255aa8f15`, 19 files.
- #211: `a13534e92b5089184cddb8df4197fceb193365be`, 15 files.
- Only overlap: `frontend/pubspec.lock`; retain #210 lock, apply #211 direct crypto dependency.

Current local status: application wiring implemented for existing-SK BYOP;
HTTP/Flutter execution and live spending remain unverified/blocked as detailed below.

New local components:

- `byop_principal.py`: separate Supabase member authentication plus live active-membership lookup. Owner V2 and owner-only guards unchanged.
- `byop_ledger.py`: principal-scoped consent, pricing interface, atomic CAS reservations, immutable execution snapshot and CALL_STARTED/no-replay protocol. Amounts are integer micro-Pollen.
- `byop_flow.py`: injected-repository orchestration reusing #210 identity verification and #211 request, builder, branding, approval and provenance contracts.
- `sql/byop_v1_candidate.sql`: local candidate membership/ledger tables, denied client access, administrative-only activation/provisioning and service-only atomic ledger CAS. Not applied to any production system.
- `tests/test_byop_v1.py`: disposable PostgreSQL/WASM ledger and membership tests plus three owner/member orchestration fixtures. Provider images use the approved reference fixture; render provenance uses a fixture. Real FFmpeg rendering remains separately exercised by #211 tests.

## Application wiring delivered locally

`byop_repository.py` uses the existing Supabase transport and retained
`pollinations_sessions` / `content_jobs` tables. `byop_v1_integration.sql` extends
the #210 credential guard for member principals, adds immutable job ownership and
request fields, and exposes service-only tenant-scoped RPCs. No parallel credential
or Content Job store was added. Owner V2 and the owner-only application guard are
unchanged. Members use Supabase `/auth/v1/user` plus current Active Membership;
client metadata cannot activate membership or grant owner authority.

The atomic dispatch RPC rechecks principal activity, current independent provider
binding, credential verification/expiry/revocation, exact job revision/request and
reservation under row locks. It commits CALL_STARTED and claims the job before
dispatch. Lost claim responses stop dispatch; started/unknown calls cannot replay.
Asset storage preserves the shared Asset Forge ZIP/manifest contract, applies
branding, and attaches content-addressed image bytes for explicit SHA-256 review.
Reviewed jobs accept a bounded user-authored PCM WAV, then reuse the existing real
FFmpeg renderer and source/output provenance gates. No external TTS is invoked.

The BYOP path supplies only the selected principal's token to the existing builder.
It never reads `POLLINATIONS_API_KEY`. Legacy workers and owner content/publishing
entry points exclude BYOP jobs, so that path cannot fall through to the retained
legacy environment-key adapter. Prompt/reference bytes and model/dimensions are
frozen for the shared builder from the execution snapshot. Existing execution and
publishing policies remain locked.

Flutter has explicit Owner BYOP and Member BYOP entry points. The member entry
reuses the existing Supabase GitHub login, without unlocking owner administration.
The shared PollinationsSessionService stores only opaque credential IDs scoped by
principal, validates ownership before selection, and retains recovery handles when
disconnect is unconfirmed. The page supports pending SK submission, verification,
explicit credential selection, job creation/recovery, bounded consent, one execution
attempt, displayed-image approval/rejection, WAV upload, render and preview. An
account or credential change invalidates local consent; no mutation auto-retries.

This supported BYOP connection path is submission of an existing SK. The retained
Owner OAuth flow is unchanged; member OAuth onboarding is not added. Independent
provider-subject evidence must already exist in the authoritative owner account or
administratively verified membership fields. Missing evidence stays pending.

## Mounted HTTP entry points

All paths below are under `/v1/byop`, require application authentication, and derive
the principal server-side. Owner administration endpoints retain their old guards.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/session` | Validate Owner V2 or Supabase + Active Membership |
| POST / GET | `/credentials` | Submit pending own SK / recover own record choices |
| GET | `/credentials/{id}` | Sanitized own credential status |
| POST | `/credentials/{id}/verify` | Provider identity check + atomic independent binding check |
| POST | `/credentials/{id}/disconnect` | Confirm persisted server revocation; upstream revocation unconfirmed |
| POST / GET | `/jobs` / `/jobs/{id}` | Create immutable CEO Content Job / retrieve own job |
| POST | `/jobs/{id}/consents` | Exact job/credential/model/count/max/expiry consent with trusted pricing |
| POST | `/executions` | Atomic reservation and durable dispatch claim; no replay |
| GET | `/jobs/{id}/executions` | Own execution/reconciliation state; never resets a call |
| GET / POST | `/jobs/{id}/asset` / `/jobs/{id}/asset-review` | Hash-verified preview / explicit approve or reject |
| POST | `/jobs/{id}/audio` | Bounded PCM WAV after approval |
| POST / GET | `/jobs/{id}/render` / `/jobs/{id}/video` | Local render / provenance-checked private preview URL |

## Remaining live/security gates

Production pricing deliberately returns 503; offline quote fixtures are not provider
pricing evidence. The separate existing live-generation policy still returns false.
No flag in this patch unlocks either gate. Before any future live execution, establish
documented model/dimension-specific maximum cost, key-specific budget evidence,
fresh provider ownership/status and an evidenced charge-reconciliation policy.
Generated images do not settle unknown charges. Reservations remain held after
CALL_STARTED/UNKNOWN/GENERATED; no public release/reconciliation endpoint is added.
Disconnect denies new claims but does not cancel an execution already claimed or
prove upstream key revocation. Membership activation, independent account evidence
and budget provisioning remain administrative, not client-controlled.

Local SQL candidates have not been applied to any real Supabase project. The
offline fixture models the existing Content Job columns; native multi-connection
Postgres contention, actual deployment schema/permissions, PostgREST RPC mapping,
Storage access and real provider behavior still need separately authorized checks.
No workers, publishing, production configuration or infrastructure were enabled.

## Offline verification

Use the existing `run_owner_v2_offline.py` seccomp runner and installed local PGlite.
The runner clears credentials and denies IPv4/IPv6 TCP/UDP socket creation.
Historical completed runs: 25 BYOP component tests and 46 #211 CEO tests passed
in separate runs before application wiring. Their automatically included 70 Owner
V2 tests were deselected; those are not claimed as passing. Current bounded runs
exercise explicitly selected non-HTTP component/repository/regression tests under
the same network-denial function, without starting TestClient. Results are recorded
in the final delivery. SQL and media tests use PostgreSQL/WASM and actual FFmpeg;
Auth/provider/storage transports are fakes. Concurrent CAS tests use the serial
PGlite bridge and do not establish native PostgreSQL multi-connection locking.

`test_byop_http.py` adds four HTTP E2E cases, including Owner/two members and
cross-tenant/body/secret isolation. They are collected but NOT RUN locally. The
sandbox denies AF_UNIX socketpair sends, which prevents TestClient/AnyIO wakeups.
No runtime recovery is retried and no test is weakened or marked skipped. Flutter
SDK is unavailable: analyzer and all Flutter tests, including the new mock service
tests, are NOT RUN on this tree. Syntax/import/OpenAPI and diff checks are separate
from HTTP/Flutter execution evidence.

## CI plan for a future authorized delivery

### Current executed results

- **117 PASS**, 0 failures, 5 deprecation warnings, 18.24 seconds in the final
  bounded network-denied run: 51 BYOP component/repository cases plus 66 selected
  non-HTTP provider, credential, content routing, render, publishing-gate and CEO
  prompt/single-character regression cases. No tests were skipped/deselected in
  that selected run. Three persistent owner/member cases executed real FFmpeg.
- Four new HTTP E2E cases collect successfully; **NOT RUN locally**.
- Full Owner V2/#210/security HTTP suites: **NOT RUN on the final tree**, because
  the established Unix socketpair restriction remains. Earlier stalled attempts
  are not passing evidence.
- Flutter analyzer/tests (including four new service mock tests): **NOT RUN**;
  Flutter/Dart SDK unavailable. No prior CI run is claimed for the local patch.
- Changed Python AST checks, runtime imports/OpenAPI generation, Node bridge
  syntax and `git diff --check`: **PASS**. Owner V2, owner-only session guard,
  global execution policy and publishing policy retain their baseline contents.

### Future authorized CI execution

Use an executor allowing AF_UNIX wakeups and install the existing requirements,
FFmpeg/ffprobe and pinned PGlite test dependency before entering network isolation.
Supply no production credentials. Set `OWNER_V2_TEST_PGLITE` to the installed
PGlite `dist/index.js`, then run the existing seccomp runner without deselection:

```sh
PYTHONPATH=backend/asset_forge:. python backend/asset_forge/tests/run_owner_v2_offline.py \
  backend/asset_forge/tests backend/tests tools/scanner/tests
```

This includes the Owner V2, #210/#211, new HTTP E2E and repository suites. Review
native contention and live-schema limitations separately; mocks are not production
proof. In an executor with the repository's required Flutter SDK:

```sh
cd frontend
flutter analyze
flutter test
```

During the local-only implementation phase, no GitHub workflow was triggered or PR updated.

## Authorized GitHub delivery and CI repair

The owner subsequently authorized commit/push, one Draft PR and bounded CI repairs.
PR #212 is Draft; #210/#211 remain untouched. No merge or deployment is authorized.
The initial integrated-head CI ran the full backend suite: 736 passed, one failed
because a retained read-only harness expects `select=` first in the queue URL.
The repair preserves the BYOP exclusion filter and reorders query parameters;
no security assertion is removed or changed. Flutter analyze found three lints
in the new page; the repair adds the required block and names callback parameters.
Both workflows now explicitly check out the PR head SHA. Backend `-rA` output
makes the four actual HTTP E2E results visible without skipping or repeating tests.
Final CI outcomes are reported in the Draft PR and delivery response, not inferred
from the initial run. The existing manual-only S1 job remains manual-only.
The next run passed Flutter analysis, all 105 Flutter tests and APK build/upload,
while backend dependency installation remained in progress for over ten minutes
before any tests. A CI-only repair bounds the backend job to 15 minutes, the
FFmpeg dependency step to six minutes, and package-network waits/retries. Existing
FFmpeg/ffprobe are reused only if both exist; both version checks and all tests
remain mandatory. No test skip, provider call or production action is introduced.

## Exact changed files

- `.github/workflows/asset-forge-backend-test.yml`
- `.github/workflows/flutter-asset-forge-test.yml`
- `backend/asset_forge/backend/asset_provider.py`
- `backend/asset_forge/backend/audio_generation.py`
- `backend/asset_forge/backend/byop_flow.py`
- `backend/asset_forge/backend/byop_ledger.py`
- `backend/asset_forge/backend/byop_principal.py`
- `backend/asset_forge/backend/byop_repository.py`
- `backend/asset_forge/backend/byop_router.py`
- `backend/asset_forge/backend/byop_runtime.py`
- `backend/asset_forge/backend/content_asset_generation.py`
- `backend/asset_forge/backend/content_jobs_api.py`
- `backend/asset_forge/backend/content_router.py`
- `backend/asset_forge/backend/final_render.py`
- `backend/asset_forge/backend/pollinations_account_inspect.py`
- `backend/asset_forge/backend/pollinations_oauth.py`
- `backend/asset_forge/backend/pollinations_oauth_router.py`
- `backend/asset_forge/backend/pollinations_sk_lifecycle.py`
- `backend/asset_forge/backend/publishing_api.py`
- `backend/asset_forge/backend/publora_publishing.py`
- `backend/asset_forge/main.py`
- `backend/asset_forge/sql/byop_v1_candidate.sql`
- `backend/asset_forge/sql/byop_v1_integration.sql`
- `backend/asset_forge/sql/owner_v2_github_session_reference.sql`
- `backend/asset_forge/sql/pollinations_owner_binding.sql`
- `backend/asset_forge/tests/owner_v2_pg_bridge.mjs`
- `backend/asset_forge/tests/test_byop_http.py`
- `backend/asset_forge/tests/test_byop_repository.py`
- `backend/asset_forge/tests/test_byop_v1.py`
- `backend/asset_forge/tests/test_content_ceo_asset_e2e.py`
- `backend/asset_forge/tests/test_pollinations_account_inspect.py`
- `backend/asset_forge/tests/test_pollinations_account_inspect_route.py`
- `backend/asset_forge/tests/test_pollinations_owner_binding.py`
- `backend/asset_forge/tests/test_pollinations_sk_lifecycle.py`
- `backend/tests/test_pollinations_oauth_session_contract.py`
- `backend/tests/test_prawtwan_chat_contract.py`
- `docs/POLLINATIONS_BYOP_V1_LOCAL.md`
- `docs/POLLINATIONS_SK_LIFECYCLE_DECISION.md`
- `frontend/lib/pages/byop_page.dart`
- `frontend/lib/pages/content_job_page.dart`
- `frontend/lib/pages/home_page.dart`
- `frontend/lib/pages/owner_oauth_uat_page.dart`
- `frontend/lib/pages/pollinations_account_inspect_page.dart`
- `frontend/lib/services/byop_service.dart`
- `frontend/lib/services/content_job_service.dart`
- `frontend/lib/services/pollinations_session_service.dart`
- `frontend/pubspec.lock`
- `frontend/pubspec.yaml`
- `frontend/test/byop_service_test.dart`
- `frontend/test/content_job_ceo_review_test.dart`
- `frontend/test/pollinations_shared_session_test.dart`
- `frontend/test/prawtwan_connection_ux_test.dart`
