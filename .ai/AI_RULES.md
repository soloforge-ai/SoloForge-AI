# SoloForge AI Engineering Rules

Version: v3.0.0

## Operating model
SoloForge AI has one owner. AI assistants are the engineering team, not a separate approval committee. Follow the owner's latest authorized task and `.ai/PROTOCOL.md`. `docs/CURRENT_SPRINT.md` is the **sole current-work status and priority reference**. Do not require, recreate or rely on `.ai/AI_CONTEXT.md`.

## Execution
- Build to completion within the owner-approved outcome and behavioral scope. Do not impose artificial three-file limits, per-file approvals or repeated approval for the same authorized action.
- Inspect relevant code, dependencies and tests; REUSE, EXTEND or REPAIR before introducing duplicate implementations.
- Edit related source, tests and affected documentation as necessary for the approved task. Avoid unrelated work.
- Refactor, move, replace or remove legacy components when necessary to deliver the authorized objective; explain meaningful compatibility and migration risks. Existing architecture is not immutable.
- Handle errors explicitly. Prefer readable, modular code and tests that verify affected behavior.
- Do not create extra status documents, lengthy audit artifacts or approval frameworks without a concrete need.

## Git
Use a development branch and conventional commits. Never commit directly to main. Commit, push, PR and merge permissions are governed by the **specific owner authorization for that task** and GitHub protections. If a complete sequence is explicitly authorized, do not request approval again for each ordinary intermediate step. If a step is excluded, do not perform it. Verify changes before merge; do not bypass failing required checks.

## Sensitive operations
Keep production mutation, deploys, destructive actions, worker enablement, external publishing and live/billable calls behind explicit action-specific owner approval. Preserve credentials, ownership validation, wallet/spending authorization, idempotency and failure containment. OAuth authentication is not spending authorization. Backups reduce recovery risk but do not eliminate external side effects. Never auto-retry ambiguous provider or publishing outcomes.

## Verification and delivery
Use proportionate tests, preferably offline/mocked. Fix test failures within scope; stop for material scope expansion or critical security issues. Report what works, what was verified and what remains blocked. A passing unit test is not proof of production E2E. A PR alone is not a finished feature.

## Priorities
Use `docs/CURRENT_SPRINT.md` for active work and `docs/ROADMAP.md` for future direction. Never automatically execute historical tasks, paused initiatives or scanner recommendations.

## Never
Never fabricate implementation evidence, conceal errors, leak secrets, bypass branch protection, silently incur provider charges, or treat a previous approval as permission for unrelated work.
