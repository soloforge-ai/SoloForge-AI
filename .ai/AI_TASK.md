# SoloForge AI Task Board

Version: v1.7.0

---

# Purpose

This document represents the current working state of the SoloForge AI project.

It provides AI assistants with a concise snapshot of active work, completed foundations, frozen initiatives, and the next safe development direction.

---

# Current Work

Title

SoloForge Product-to-Post — Text Model Qualification + E2E Preparation

Status

In Progress

Primary Source of Truth

`docs/CURRENT_SPRINT.md`

---

# Active Product Objective

Prove the original commercial workflow with one real product:

```text
Product
→ Extract / load product data
→ Evaluate product opportunity
→ Select selling angle
→ Generate creative + caption
→ Review
→ Export ready-to-post package
```

The next product milestone must prove this flow before unrelated architecture expansion.

---

# Completed In Current Cycle

- Cleanup Scope Reset #1 merged.
- Product-to-Post is the active product direction.
- Chat Prawtwan and Developer Tools Home entry points were removed.
- Confirmed dead/legacy Flutter Product/Sticker/Test implementations were removed.
- Text Model Qualification Harness merged.
- Live Text Qualification Runner merged and is available through GitHub Actions.

---

# Current Gate

1. Obtain a usable live qualification result for a text provider.
2. Treat workflow execution success and model qualification success as separate outcomes.
3. Do not switch the production ContentEngine provider without explicit owner approval.
4. Inspect the existing Product Forge path for only the smallest missing Product-to-Post gaps.
5. Run one real product end-to-end and verify a useful, reviewable, manually exportable ready-to-post package.

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

Income Engine P1 remains valid historical work. `P2 — Opportunity Library v0` and later Income Engine expansion are frozen and must not proceed unless the owner explicitly re-authorizes them.

---

# Verified Shared Foundations

Retain shared infrastructure only where it supports active components or has an existing runtime dependency.

Current examples include:

- Product Catalog and discovery
- Feed Processor and MiniBoss
- Product Intelligence and Product Forge
- Content Engine and prompt infrastructure
- Pollinations OAuth/session handling used by Asset Forge
- Character Memory bridge currently used by Asset Forge runtime
- Asset Forge output-quality processing
- Text Model Qualification Harness
- Live Text Qualification Runner

Do not expand these systems merely because future extensions are possible.

---

# Product Principle

SoloForge should produce useful business output, not merely accumulate subsystems.

For the active cycle, the governing question is:

> Can one real product enter SoloForge and leave as a useful, reviewable, ready-to-post package?

Engineering completion alone is not sufficient if the user still cannot complete that product workflow.

---

# Explicit Non-Goals

Do not add or expand without explicit owner approval:

- new agents
- new memory systems
- billing
- autonomous posting
- unrelated verticals
- broad architecture refactors
- Income Engine P2+

---

# AI Instructions

When starting a new task:

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Review this task board.
5. Read `docs/CURRENT_SPRINT.md` for human-approved development state.
6. Prefer ACTIVE/current Product-to-Post decisions over superseded or frozen Income Engine direction.
7. Treat Asset Forge v1 as a retained component, not the active roadmap by default.
8. Do not restart Income Engine expansion, Chat Prawtwan expansion, Idea Flow expansion, or unrelated infrastructure without explicit owner approval.
9. Prefer the smallest change that advances the real Product-to-Post workflow.
10. Do not infer human intent from generated scanner output.

---

# Notes

Human-approved active development state lives in `docs/CURRENT_SPRINT.md`.

Generated scanner reports describe observed implementation and must not replace human sprint state.

`docs/ROADMAP.md` is currently scanner-generated and must not be treated as authoritative product intent until its ownership is corrected in a separate approved change.

---

End of Task Board
