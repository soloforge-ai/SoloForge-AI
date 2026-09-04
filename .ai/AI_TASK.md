# SoloForge AI Task Board

Version: v1.5.0

---

# Purpose

This document represents the current working state of the SoloForge AI project.

It provides AI assistants with a concise snapshot of active work, completed foundations, and the next safe development direction.

---

# Current Work

Title

SoloForge Income Engine — P1 Income Diagnostic v0

Status

Validated — PASS

Primary Spec

`docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`

---

# Goal Achieved

SoloForge now has a validated beginner-safe diagnostic contract that can produce meaningfully different normalized profiles without inventing unknown skills or generating income recommendations prematurely.

The diagnostic preserves evidence-backed capability, urgency, time, budget, devices, work preferences, customer/public-facing tolerance, existing assets, risk, and market reach for later opportunity matching.

---

# P1 Completed Scope

- 15 diagnostic questions
- normalized user profile output
- evidence/confidence trace for inferred capabilities
- skill-discovery mode when the user does not know what they are good at
- 10 deliberately different persona tests completed
- materially different profiles produced
- hard constraints preserved
- unknown skills retained as unknown
- no recommendation generated during validation
- explicit PASS gate satisfied

---

# P1 Validation Result

**PASS**

The validation includes the required persona categories:

1. Data / spreadsheet-oriented person
2. Strong speaker with social-media familiarity
3. Visual creator who dislikes customer interaction
4. Existing small seller
5. Beginner with no identified skill
6. Student with low budget
7. Full-time worker with little available time
8. Unemployed person with substantial available time
9. Person with money but little time
10. Person with almost no money but strong willingness to work

The detailed evidence is in `docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`.

---

# Guardrails Carried Forward

Future phases must:

- preserve evidence and confidence instead of inventing capability
- enforce hard constraints before ranking opportunities
- distinguish tool exposure from demonstrated skill
- distinguish willingness to work from proven capability
- use controlled opportunity metadata rather than free-form LLM popularity guesses
- validate real-user action and market response later, not only recommendation satisfaction

---

# P1 Must Remain Closed

Do not add these retroactively to P1:

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

These belong to later phases only if explicitly approved.

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 after owner-accepted Android E2E evidence on 2026-09-04.

Its default product contract remains 4 poses / 1 AI generation, with local review/fix/export and no automatic paid regeneration.

GitHub Issue #48 tracks residual light fringe as non-blocking output polish.

Chat Prawtwan MVP and the Supabase-backed Telegram Idea Inbox webhook remain merged capabilities but are not the current Income Engine focus.

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

P1 is complete.

The next candidate phase is:

`P2 — Opportunity Library v0`

P2 should define a controlled set of income opportunities and their requirements before any personalized ranking engine exists.

Do not start P2 until the owner explicitly approves progression.

---

# AI Instructions

When starting a new task:

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Review this task board.
5. Read docs/CURRENT_SPRINT.md for human-approved development state.
6. Read docs/INCOME_ENGINE_P1_DIAGNOSTIC.md for the completed P1 contract and validation evidence.
7. Prefer ACTIVE/current decisions over stale or superseded context.
8. Do not reopen completed Asset Forge v1 scope without an explicit blocker or owner priority.
9. Do not implement P2 until the owner explicitly approves progression.

---

# Notes

Long-term planning belongs in docs/ROADMAP.md.

Human sprint documentation belongs in docs/CURRENT_SPRINT.md.

Generated scanner reports must not replace human sprint state.

---

End of Task Board
