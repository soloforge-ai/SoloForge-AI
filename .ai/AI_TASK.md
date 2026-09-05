# SoloForge AI Task Board

Version: v1.6.0

---

# Purpose

This document represents the current working state of the SoloForge AI project.

It provides AI assistants with a concise snapshot of active work, completed foundations, frozen initiatives, and the next safe development direction.

---

# Current Work

Title

SoloForge Product-to-Post — Cleanup Scope Reset #1

Status

In Progress

Primary Source of Truth

`docs/CURRENT_SPRINT.md`

---

# Active Product Objective

Restore SoloForge to the original commercial workflow:

```text
Product
→ Extract / load product data
→ Evaluate product opportunity
→ Select selling angle
→ Generate creative + caption
→ Review
→ Export ready-to-post package
```

The next product milestone must prove this flow with one real product before unrelated architecture expansion.

---

# Cleanup #1 Approved Scope

- keep Product Catalog and discovery
- keep Feed Processor and MiniBoss
- keep Product Intelligence and Product Forge
- keep Content Engine
- keep Asset Forge as a reusable creative/image-processing component
- keep Pollinations OAuth/session infrastructure used by Asset Forge
- keep Asset Forge Memory/output-quality dependencies that are currently wired into runtime
- remove Chat Prawtwan navigation from Home
- remove Developer Tools navigation from Home
- remove confirmed dead/legacy Flutter Product/Sticker/Test implementations
- update project state documentation to Product-to-Post

---

# Explicit Non-Goals For Cleanup #1

Do not:

- modify backend Prawtwan routes
- modify Idea Flow / Telegram webhook backend routes
- delete Supabase Idea Flow migrations
- refactor Asset Forge
- remove shared Pollinations OAuth/session code
- remove Asset Forge Memory/output-quality runtime dependencies
- add new Product-to-Post features in the cleanup PR
- add billing
- add autonomous posting
- add agents or new memory systems

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 after owner-accepted Android E2E evidence on 2026-09-04.

Its default product contract remains 4 poses / 1 AI generation, with local review/fix/export and no automatic paid regeneration.

GitHub Issue #48 tracks residual light fringe as non-blocking output polish.

---

# Frozen Capabilities / Initiatives

The following remain in the repository but are not active roadmap drivers:

- Chat Prawtwan MVP
- Supabase-backed Telegram Idea Inbox / Idea Flow
- SoloForge Income Engine P1

Income Engine P1 remains valid historical work, but its candidate `P2 — Opportunity Library v0` is frozen and must not begin unless the owner explicitly re-authorizes it.

---

# Verified Shared Foundations

Retain shared infrastructure only where it supports active components or has an existing runtime dependency.

Current examples include:

- Pollinations OAuth/session handling used by Asset Forge
- Character Memory bridge currently used by Asset Forge runtime
- Asset Forge output-quality processing
- existing Product Catalog / MiniBoss / Product Intelligence foundation

Do not expand these systems merely because future extensions are possible.

---

# Product Principle

SoloForge should produce useful business output, not merely accumulate subsystems.

For the active cycle, the governing question is:

> Can one real product enter SoloForge and leave as a useful, reviewable, ready-to-post package?

Engineering completion alone is not sufficient if the user still cannot complete that product workflow.

---

# Next Development Direction

After Cleanup Scope Reset #1 is merged, inspect the existing Product Forge path and identify the smallest missing gaps needed for one real end-to-end Product-to-Post run.

Prioritize workflow completion over architecture expansion.

---

# AI Instructions

When starting a new task:

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Review this task board.
5. Read docs/CURRENT_SPRINT.md for human-approved development state.
6. Prefer ACTIVE/current Product-to-Post decisions over superseded Income Engine direction.
7. Treat Asset Forge v1 as a retained component, not the active roadmap by default.
8. Do not restart Income Engine P2, Chat Prawtwan expansion, Idea Flow expansion, or unrelated infrastructure without explicit owner approval.
9. Prefer the smallest change that advances the real Product-to-Post workflow.

---

# Notes

Long-term planning belongs in docs/ROADMAP.md.

Human sprint documentation belongs in docs/CURRENT_SPRINT.md.

Generated scanner reports must not replace human sprint state.

---

End of Task Board
