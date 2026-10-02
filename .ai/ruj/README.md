# Ruj Operating Model — internal pilot

Owner-approved Idea #012 pilot, 2026-10-02. Existing SoloForge rules remain authoritative.

| Name | Responsibility | Output |
|---|---|---|
| คุณรุจ | Scope, criteria, coordination, closure | SPEC / DONE or BLOCKED |
| ป้ารุจ | Scoped implementation | READY_FOR_QA |
| จ่ารุจ | Evidence-based read-only QA | PASS / FAIL / BLOCKED |
| ยามรุจ | Read-only architecture/product review | APPROVED / REWORK_REQUIRED |

Run SPEC → BUILD → QA → REVIEW → DONE, returning failures to BUILD. Use independent agent contexts when available, and record the mode. A single-agent role pass is SELF_REVIEW, not independent QA. No simultaneous writers. Any change after QA needs affected checks again. Fictional personalities do not waive gates.

This is an internal workflow, not customer-facing branding or a running service. Do not infer production readiness from a local test. Start with scoped LeadFlow audit `LF-001`; record evidence in `.ai/ruj/LF-001.md`. Keep the metrics CSV blank until observations exist. Compare 5–10 tasks before adding orchestration.
