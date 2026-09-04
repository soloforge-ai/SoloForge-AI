# SoloForge AI Task Board

Version: v1.4.0

---

# Purpose

This document represents the current working state of the SoloForge AI project.

It provides AI assistants with a concise snapshot of active work, completed foundations, and the next safe development direction.

---

# Current Work

Title

SoloForge Income Engine — P1 Income Diagnostic v0

Status

In Validation

Primary Spec

`docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`

---

# Current Goal

Validate whether SoloForge can collect enough beginner-safe, evidence-based information about a user to support later personalized income-path decisions without defaulting to generic online-income advice.

P1 must understand the user before any opportunity recommendation is attempted.

---

# P1 Scope

- 15 diagnostic questions covering income goal, urgency, time, budget, devices, tool familiarity, observed skill signals, work preferences, customer interaction tolerance, camera/voice tolerance, existing assets, sales-model tolerance, risk, languages/market reach, and unknown-skill fallback
- normalized profile output
- evidence/confidence trace for inferred capabilities
- skill-discovery mode when the user does not know what they are good at
- validation against 10 deliberately different personas
- explicit PASS/FAIL gate

---

# P1 Must Not Add

Do not implement these during P1:

- Opportunity Library
- income-path recommendations
- ranking/scoring engine
- Flutter UI changes
- Supabase schema
- billing
- scraping
- autonomous agents
- paid AI generations
- income guarantees

P1 is a validation/specification phase only.

---

# P1 Acceptance Gate

The same diagnostic must be run against 10 distinct personas.

P1 passes only if:

- beginners can answer without business jargon
- materially different inputs produce materially different normalized profiles
- unknown skills remain unknown instead of being fabricated
- hard constraints such as time, budget, devices, urgency, and public-facing tolerance are preserved
- every inferred capability can be traced back to evidence
- no recommendation is generated before the opportunity model exists
- the output is sufficient for P2 Opportunity Library + scoring work

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 after owner-accepted Android E2E evidence on 2026-09-04.

Its default product contract remains 4 poses / 1 AI generation, with local review/fix/export and no automatic paid regeneration.

GitHub Issue #48 tracks residual light fringe as non-blocking output polish.

Chat Prawtwan MVP and the Supabase-backed Telegram Idea Inbox webhook remain merged capabilities but are not the active product priority in P1.

---

# Verified Foundation Capabilities

Memory Foundation v1 remains available as shared infrastructure:

- Decision Memory
- ACTIVE / SUPERSEDED lifecycle
- scoped Decision retrieval
- authority validation
- JSON persistence
- append-only Memory Events
- event retrieval/filtering
- image-generation runtime events
- Runtime Test Runner
- end-to-end Memory Foundation verification

Previous verification:

```text
Ran 12 tests in 0.183s
OK
```

---

# Product Principle

SoloForge should reduce wrong experiments, not merely generate more ideas.

Future recommendation logic should answer:

> Given this person's real constraints and evidence, what is the highest-probability income experiment to test first?

—not:

> What are some popular ways to make money online?

---

# Next Development Direction

Execute the P1 diagnostic against 10 test personas and review whether the normalized profiles are meaningfully different.

Do not start P2, recommendation logic, or UI work before P1 passes and the owner approves the next phase.

---

# AI Instructions

When starting a new task:

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Review this task board.
5. Read docs/CURRENT_SPRINT.md for human-approved development state.
6. Read docs/INCOME_ENGINE_P1_DIAGNOSTIC.md for the active P1 contract.
7. Prefer ACTIVE/current decisions over stale or superseded context.
8. Do not reopen completed Asset Forge v1 scope without an explicit blocker or owner priority.
9. Do not implement P2 until P1 validation passes and the owner approves progression.

---

# Notes

Long-term planning belongs in docs/ROADMAP.md.

Human sprint documentation belongs in docs/CURRENT_SPRINT.md.

Generated scanner reports must not replace human sprint state.

---

End of Task Board
