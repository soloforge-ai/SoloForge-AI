# RUJ PERFORMANCE PILOT v1 — Controlled GitHub Trial

**Status:** PROPOSED / NOT STARTED  
**Owner decision:** approved to create a draft pilot plan and select the first task; implementation/merge/deploy not authorized here.  
**Reference:** `.ai/ruj/README.md`, `.ai/ruj/quality-gate.md`, `.ai/ruj/pilot-metrics.csv`. Existing rows are historical **SELF_REVIEW**, not an independent-agent baseline.

## Objective and hypothesis

Test whether a structured RUJ TEAM OS workflow reduces elapsed time to review-ready completion, without increasing defects, owner interruptions or operating cost. Hypothesis for decision-making, not a promise: at least **20% median time reduction** at comparable task complexity, with no evidence of lower quality.

## Design

- **10 new GitHub-scoped tasks**, in matched pairs by risk and estimated complexity: 5 **BASELINE** (single-agent conventional execution) and 5 **RUJ** (SPEC → BUILD → QA → REVIEW → DONE).
- Alternate the first mode per pair to limit ordering/learning effects. Assignment must be recorded **before work**; do not switch mode after results are known.
- No previous PRs (#155–#157) count as timed samples; they may be calibration material only.
- Select tasks from small, owner-approved backlog items, ideally a mix of docs, test fixes, UI and backend. Avoid production writes/migrations, enabling workers, merging, deploying, and unscoped refactors.
- A GitHub Action passing is CI evidence; it is not proof of independent QA.
- If independent agent contexts are unavailable, label role simulation `SELF_REVIEW` (or `RUJ_SELF_REVIEW` for reporting) and do not treat it as evidence for an autonomous multi-agent productivity claim.

## Clock definitions and measurement

**Start:** owner-approved task specification + assigned execution mode, immediately before agent begins task work.  
**Review-ready stop:** final commit is available, all required CI results received, and required QA/reviewer evidence recorded (or explicitly BLOCKED).  
**Closure:** separate timestamp for owner acceptance; never hide waiting for owner within claimed agent execution time.  
Use UTC ISO-8601 timestamps and preserve PR/Actions URLs as evidence.

Track three non-interchangeable durations:
- `elapsed_minutes`: end-to-end start → review-ready (includes CI and idle waits).
- `active_minutes`: measured hands-on execution and orchestration time, including prompt/review activity.
- `ci_wait_minutes`: time spent waiting on required CI, including reruns.
- `owner_wait_minutes`: time awaiting owner response, excluded from review-ready metric or separately reported if work could not proceed.

Every retry and rework is part of the measured period. Missing timestamps ⇒ `UNMEASURED`, not zero.

## Quality and cost measures

- `first_pass_success`: all defined critical gates pass on first QA submission.
- `rework_count`: number of returns from QA/Review to Build.
- `escaped_errors`: confirmed post-close defects, with observation date/window; unknown ≠ zero.
- `decision_reversal_count`: owner/reviewer reversals requiring rework.
- `owner_interventions`: substantive clarifications/approval requests needed after start.
- `operating_cost_estimate`: provider/tool cost with currency and evidence. If usage or rates unavailable, write `UNKNOWN`, never invent.
- `qa_mode`: `INDEPENDENT_AGENT`, `SELF_REVIEW`, or `HUMAN_REVIEW`; document actual separate sessions/actors.
- `scope_risk`: LOW/MEDIUM/HIGH; include simple estimate of story points or acceptance criteria count prior to assignment.

## RUJ roles and gating

| Gate | Role | Required evidence |
| --- | --- | --- |
| SPEC | คุณรุจ | issue/task scope, exclusions, acceptance criteria, risk, mode and start timestamp |
| BUILD | ป้ารุจ | scoped branch/diff/commit, implementation/test evidence, READY_FOR_QA |
| QA | จ่ารุจ | tested final SHA; positive/negative/regression checks; PASS/FAIL/BLOCKED |
| REVIEW | ยามรุจ | architecture, security, cost/maintainability review of same SHA |
| DONE | คุณรุจ | record in ledger; explicit distinction between review-ready, merge, deploy and production |

Only Builder writes implementation files. QA and Reviewer are read-only. Any Build changes after QA reset affected gates. No simultaneous writers and no bypass on missing independent review. Pilot does not grant merge/deploy permissions.

## Measurement schema

Retain the current `pilot-metrics.csv` unchanged for historical backward compatibility. For **new** tasks, write one row each to `performance-pilot-v1.csv` using the header committed alongside this plan. Use `task_id` to link each row to a task log `.ai/ruj/performance/tasks/<task_id>.md`, issue and PR.

- Record metrics as observations, never fabricate.
- For blocked tasks, capture reason and time; do not silently exclude from the denominator.
- Compare median elapsed time and active time for paired task categories and show per-pair differences. Show overall 5-vs-5 as descriptive because sample size is small.
- Report CI wait separately; calculate percent time reduction as `(median_baseline - median_ruj) / median_baseline * 100` only when baseline > 0.
- Report rework, first-pass rate, confirmed escaped defects, intervention and cost side by side.
- No definitive causal or statistical significance claim based only on 10 tasks.

## First candidate — RP-001 (CALIBRATION, NOT A TIMED SAMPLE)

**Task:** Audit PR #156 `Product Reference Upload` against the existing RUJ Quality Gate, read-only.

**Scope:** inspection of Storage public-read assumption, partial-upload orphan files, status races, product QA vs grounding readiness, uploaded file limits, API error behavior, and mobile picker behavior; link evidence to PR commit.  
**Deliverable:** one Task SPEC and read-only QA/Review report with PASS/FAIL/BLOCKED and prioritized issues.  
**Excluded:** production Storage access, deploying, merging, changing bucket policy, actual mobile hardware tests unless explicitly provided.

**Why calibration:** PR #156 started before the measurement protocol. Use it to verify that the RUJ gates work, not to claim time savings or count in the ten-task experiment.

### First measured task selection

After RP-001, คุณรุจ should propose the first new **matched pair** from the approved backlog, record complexity and mode assignment *before* execution, and obtain scoped owner approval for code writes. Do not invent work or treat this plan approval as permission to change arbitrary code.

## Safety / stop conditions

Halt with `BLOCKED` on missing permissions, ambiguous external side effects, unsupported access, missing tests for high-severity issues or unclear production isolation. No production workers, Supabase data/bucket mutations, merges, deployments, auto-publish, or background autonomous GitHub agents under this PR.

## Pilot decision

Proceed toward automation only if the paired observations justify it: >=20% median elapsed reduction, no worse quality/escaped errors (within observable follow-up), and tolerable incremental cost/owner load. Otherwise reduce orchestration overhead or continue with manual RUJ protocol.
