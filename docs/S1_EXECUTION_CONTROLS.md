# S1 fail-closed execution controls

Base: `3611f73853915d6254c0f4c4427106fe3073fffd`.
This patch is an execution lock, not permission to spend or enable automation.

## Process startup

- Embedded loops default OFF (`SOLOFORGE_RUN_EMBEDDED_WORKERS`).
- Dedicated loops independently default OFF (`SOLOFORGE_RUN_DEDICATED_WORKERS`).
- Only `1`, `true`, `yes`, `on` enable process startup (case-insensitive,
  surrounding whitespace ignored). Missing, empty and other values disable it.
- Disabled startup emits a fixed non-sensitive diagnostic. The dedicated process
  exits normally without starting loops. Successful service startup is not
  evidence that automation is authorized.
- These flags are process controls only. Neither supplies owner approval,
  OAuth wallet ownership, a quote, or budget authorization.

## Generation remains locked

`backend/asset_forge/backend/execution_policy.py` deliberately returns false for
execution authorization. S1 has no environment/request-based spending override.
The missing trusted owner/approval/budget verifier is a later separately approved
scope; replacing this lock requires review and independent evidence.

- Idea `generate`, approve, continue and regenerate reject execution with HTTP
  503 before mutation or background-task scheduling. Existing authentication and
  validation still apply. Drafts, retries and job status are not erased.
- API resume helpers and Telegram content resume reject dispatch too.
- Content generation, routing, asset, audio and render polling/job entry points
  return without queue reads, claims, recovery resets or writes. Existing backlog
  is not drained even if process flags were already enabled.
- Direct Asset Forge image edit, content text generation, asset provider,
  Prawtwan chat and retained root Pollinations image adapter have boundary locks.
  A connected OAuth session is not spending authorization. There is no key fallback
  that bypasses this lock.
- Sales Inbox skips its external LLM chain and retains deterministic local text.
- Authenticated queue reads, local idea analysis, save-to-backlog, prompt building,
  image post-processing and no-OAuth legacy local sheets remain available. Local
  sheets retain the explicit `local_fallback` mode; single-character provider
  generation remains unavailable. Connected provider requests reject rather than
  silently substituting a successful local result.

## Deliberately unchanged / not proven

No schema, migrations, OAuth architecture, wallet accounting, claim RPCs,
provider retry algorithms, publishing submission logic, workflows or production
configuration are changed. Legacy retry/fallback algorithms are retained behind
an unreachable production execution boundary, not approved for reactivation.

Publishing status synchronization is still the existing loop when a process is
explicitly enabled; it does not create a post. Manual publish/schedule routes and
existing Publora schedules are unchanged. S1 does not prove their authorization or
halt externally scheduled posts. Separate publishing review is required.

Scheduled Production Smoke still contains a production generation POST (S2).
Without OAuth it can still produce a labelled local sheet; it is not converted
into a read-only smoke by this PR. Manual QA scripts and other runtimes outside
Asset Forge are not enabled or certified by S1. No claim is made that all external
scripts have been locked, or that mocked tests prove production billing safety.

## Validation / rollout

Run the existing offline backend/scanner suite:

```sh
PYTHONPATH=backend/asset_forge:. python -m pytest -q \
  backend/asset_forge/tests backend/tests tools/scanner/tests \
  backend/asset_forge/test_character_memory_bridge.py
python -m compileall -q backend/asset_forge backend/pollinations_image.py backend/tests
```

S1 tests use fake tokens, denied network and provider spies. Explicit enablement
starts only mocked loops. Selected old processing-contract tests replace a guard
inside that test only; new denial tests always exercise the real closed policy.
No live credentials, database, generation or publishing calls are required.

Review and approve the intentional 503 behavior before rollout. Do not turn flags
on, reconnect accounts, retry queued work or deploy as part of this PR. Live
execution remains NO-GO pending the separately reviewed identity, budget, claim,
reconciliation and provider integration work. S1 does not authorize merge/deploy.


## Verified offline integration checkpoint — 2026-10-21

- Verification branch: `test/s1-offline-verification-20261021`.
- Verified branch commit: `7155723d34956ad86f6a08317de2c5b16f7201e9` (pre-documentation change).
- Compared main commit: `a2fd5fcbbf1a1cf5dcd43b60db4a104a6027ce22`.
- GitHub Actions run: https://github.com/soloforge-ai/SoloForge-AI/actions/runs/39551691493
- CI result: `s1-offline-verification` SUCCESS; `48 passed, 44 warnings` in the S1 execution-policy test suite. The separate `backend-test` job was skipped for the manual dispatch.
- Isolation: Docker test execution used `--network none`, `--cap-drop ALL`, `--security-opt no-new-privileges`, and a read-only filesystem; container network-isolation preflight passed. Dependencies were installed during image build, before isolated test execution.
- Source comparison at the recorded commits: S1 application controls and tests were unchanged between the branch and `main`. The branch-only change was `.github/workflows/asset-forge-backend-test.yml` (62 additions).
- Evidence scope: offline CI tests with mocks/fakes, not production E2E proof. No live provider spending, publishing, worker enablement, or production authorization is established by this checkpoint.
- Remaining review: integrate the offline-verification workflow into `main` through a separately authorized PR/review process. Do not merge, deploy, enable workers, or call live/billable providers without action-specific owner approval.
- Evidence reuse: recheck only if the relevant source, workflow, runtime assumptions, or verification baseline changes materially; do not rerun identical checks without a documented reason.
