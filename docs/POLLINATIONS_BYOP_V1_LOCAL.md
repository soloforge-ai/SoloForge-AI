# BYOP V1 local application wiring — verification limited by sandbox

Local branch: `local/pollinations-byop-v1`; original worktree remains untouched.
HEAD: `4bc9f8a179836fb04c4300a5c93ccb7c7ff6228c` (no new commit).
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

No GitHub workflow was triggered or PR updated in this task.

## Exact changed files

- `.github/workflows/asset-forge-backend-test.yml`
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
