# SoloForge AI Development Protocol

Version: v3.0.0

## Purpose
SoloForge AI is a single-owner product under active development. Optimize for completing useful, verified product work with minimal overhead. The owner makes product, architecture, priority and risk decisions; AI agents execute within explicitly authorized scope.

## Source of truth
1. Explicit current owner instruction and task authorization.
2. This protocol and `.ai/AI_RULES.md` for execution standards.
3. `docs/CURRENT_SPRINT.md` — the human-maintained current-work priority, scope and owner-decision source; operational status requires live evidence reconciliation.
4. `docs/ROADMAP.md` — longer-term direction, not automatic execution authorization.
5. Source code and tests — evidence of implementation, not permission.

`.ai/AI_CONTEXT.md` is retired. Do not read it as required startup context, update it, or recreate a replacement status document. Historical task boards, checkpoints, PRs and generated scanner outputs are evidence only, never standing authorization.

## Live state reconciliation
Before planning, resuming or reporting implementation status, reconcile relevant, current evidence from GitHub, CI, Supabase, Render and other affected systems. Inspect only what is necessary for the task, using read-only checks unless writes are separately authorized.

`docs/CURRENT_SPRINT.md` is human-maintained and authoritative for owner-directed priorities, scope and decisions, but it is not automatic or conclusive evidence of implementation, migration, deployment or runtime state.

- Distinguish `NOT IMPLEMENTED`, `NOT VERIFIED`, `NOT DEPLOYED` and `UNKNOWN`. Missing verification is not proof that implementation is missing.
- Verify relevant commits/merged PRs, tests, database migrations, deployment versions and runtime configuration before declaring work incomplete. Cite the environment and evidence actually checked.
- Reuse verified completed work. Never rebuild, duplicate or reopen work solely because a document has not been updated.
- If documentation conflicts with current verified evidence, report `DOCUMENTATION DRIFT`; preserve owner decisions and do not silently rewrite them.
- If access or evidence is unavailable, state the precise verification limitation rather than declaring the entire initiative blocked.
- Update `CURRENT_SPRINT.md` only within an authorized write scope; never let automated status sync override owner priorities or decisions.

**Operational state is established by current evidence; authorization and priority are established by owner decisions.**

## Build-to-completion workflow
For an owner-approved task: inspect only relevant implementation and tests; reuse or repair existing components where practical; implement the end-to-end change; run proportionate offline tests; fix failures inside the approved scope; report the delivered outcome and genuine blockers. Do not insert repeated approval gates for ordinary decisions inside the same authorized action. Do not create process documents by default.

Scope is defined primarily by the approved **objective and affected behavior**, not an arbitrary file-count ceiling. Agents may edit the files necessary to complete that objective, including related tests and documentation, while avoiding unrelated changes. Refactoring or replacing legacy architecture is permitted when necessary for the owner-approved outcome; explain meaningful tradeoffs. Stop for material scope expansion, irreversible consequences or newly discovered critical security risk.

## Git and release authorization
Work on a development branch, never commit directly to main. A Git operation is allowed only if explicitly authorized for the current task. When the owner authorizes a complete delivery sequence (edit, commit, push, PR and/or merge), carry out the authorized sequence without requesting redundant approvals, subject to successful verification and applicable repository protections. Do not infer authorization for omitted steps. A task-specific prohibition overrides general workflow language. Never bypass required GitHub checks or branch protections.

Production deployments, production data changes, destructive operations, external publishing, worker enablement and live/billable provider calls require explicit action-specific authorization and applicable budget/security controls. A backup does not by itself authorize irreversible actions. Do not deploy merely because a PR was merged.

## Security and verification
Protect credentials and personal data. Preserve owner authorization, spending controls, idempotency and fail-closed behavior on sensitive paths. Use offline mocks/fakes for tests when feasible. Do not retry ambiguous external side effects. Distinguish local test evidence, CI and production proof. Do not claim success without verification.

## Communication
Lead with outcome. Keep reports concise: changed behavior/files, verification performed and results, remaining risks or blockers. Use PASS/FAIL/BLOCKED tables for requested audits rather than routine development updates. No new approval matrix or duplicated status documentation.

## Recovery
Use Git and the owner's backups for recovery. On interrupted work verify the actual branch and commit before resuming; reuse verified completed work instead of restarting. Owner decisions override stale checkpoints.

## Completion
A task is complete when the requested behavior is implemented and adequately verified, not merely when a patch or PR exists.
