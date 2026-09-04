# SoloForge AI Task Board

Version: v1.3.0

---

# Purpose

This document represents the current working state of the SoloForge AI project.

It provides AI assistants with a concise snapshot of active work, completed foundations, and the next safe development direction.

---

# Current Work

Title

Asset Forge v1 — Working Product #1

Status

Completed

Verification

Owner-accepted Android end-to-end evidence completed on 2026-09-04.

---

# Goal Achieved

SoloForge AI now has a working Asset Forge product path that connects Pollinations, generates one four-pose 2x2 sticker sheet in one AI generation, previews the result, and produces four individual sticker PNG outputs.

The default product contract remains 4 poses / 1 AI generation. Review, local fix, and export must not silently add paid generations.

---

# Completed Product Scope

- Pollinations OAuth connection path
- Asset Forge Android workflow
- canonical character master routing
- explicit character color override
- 3D chibi v1 scope lock
- four-pose 2x2 Quick Pack
- generated sheet preview
- four individual sticker outputs
- local review/fix/export flow
- no remove.bg dependency in the default product flow
- Chat Prawtwan MVP merged
- Supabase-backed Telegram Idea Inbox webhook merged

---

# Known Non-Blocking Backlog

GitHub Issue #48 tracks residual white/light matte or fringe around some exported sticker edges.

This is P1 output polish. It does not reopen Asset Forge v1 and must not trigger extra live Pollen generation unless the owner explicitly prioritizes it.

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

# Out of Scope Unless Explicitly Approved

Do not add these automatically:

- Asset Forge pack sizes above four
- automatic paid sticker regeneration
- general authentication
- history
- SoloForge billing
- video/audio generation
- Vector DB
- Graph DB
- autonomous memory deletion
- required embeddings
- memory visualization / 3D brain
- nightly consolidation / dreaming

---

# Next Development Direction

There is no active implementation sprint after the Asset Forge v1 closure.

Do not continue Asset Forge polish by default. The next task should be selected by the owner based on expected business/product value, recurring revenue potential, automation leverage, or another explicit SoloForge priority.

When future systems need durable memory, integrate them incrementally through the approved Memory Foundation contracts rather than creating separate memory implementations.

---

# AI Instructions

When starting a new task:

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Review this task board.
5. Read docs/CURRENT_SPRINT.md for human-approved development state.
6. Prefer ACTIVE/current decisions over stale or superseded context.
7. Reuse Memory Foundation v1 when durable decisions or runtime events are required.
8. Do not reopen completed Asset Forge v1 scope without an explicit blocker or owner priority.

---

# Notes

Long-term planning belongs in docs/ROADMAP.md.

Human sprint documentation belongs in docs/CURRENT_SPRINT.md.

Generated scanner reports must not replace human sprint state.

---

End of Task Board
