# SoloForge AI assistant entry point

Follow `.ai/PROTOCOL.md`, `.ai/AI_CONTEXT.md`, `.ai/AI_RULES.md`, `.ai/AI_TASK.md`, and `docs/CURRENT_SPRINT.md` in their established priority, with explicit owner instructions first.

For owner-requested Ruj pilot tasks, use `.ai/ruj/README.md` and `.ai/ruj/quality-gate.md`.
The roles are คุณรุจ (Main), ป้ารุจ (Builder), จ่ารุจ (QA), and ยามรุจ (Reviewer).
Only Main closes a task after evidence for the final revision. Do not claim that a role prompt runs persistently.

## Autonomous development handoff (owner-approved Phase 2B)

For explicitly owner-approved autonomous coding tasks, follow the bounded execution contract in `.ai/PROTOCOL.md` and `.ai/AI_RULES.md`. Approval of these instructions alone does **not** authorize code changes, provider calls, merges, deployments, or production data access. Use existing Ruj roles only when separately requested; do not claim persistent agents.
