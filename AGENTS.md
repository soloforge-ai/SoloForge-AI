# SoloForge AI assistant entry point

Read `.ai/PROTOCOL.md` and `.ai/AI_RULES.md`, then consult `docs/CURRENT_SPRINT.md` for current owner-approved priorities. `.ai/AI_CONTEXT.md` is retired and must not be required as startup context. Explicit owner instructions come first; `.ai/PROTOCOL.md` and `.ai/AI_RULES.md` govern execution, while `docs/CURRENT_SPRINT.md` governs current development intent. Conflicting task-board entries and historical task records do not authorize work.

For owner-requested Ruj pilot tasks, use `.ai/ruj/README.md` and `.ai/ruj/quality-gate.md`.
The roles are คุณรุจ (Main), ป้ารุจ (Builder), จ่ารุจ (QA), and ยามรุจ (Reviewer).
Only Main closes a task after evidence for the final revision. Do not claim that a role prompt runs persistently.

## Autonomous development handoff (owner-approved Phase 2B)

For explicitly owner-approved autonomous coding tasks, follow the bounded execution contract in `.ai/PROTOCOL.md` and `.ai/AI_RULES.md`. Approval of these instructions alone does **not** authorize code changes, provider calls, merges, deployments, or production data access. Use existing Ruj roles only when separately requested; do not claim persistent agents.
