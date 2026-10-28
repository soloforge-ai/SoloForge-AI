# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

**Owner Identity V2 — P0 (owner-directed priority, 2026-10-24)**

## Current Implementation

**Owner Identity V2: isolated Owner Registry and passwordless backend — implemented; offline verified; activation pending**

## Status

The local implementation provides an additive migration, administrator-only bootstrap, independent email-code authentication, opaque V2 sessions and offline security tests. V2 defaults OFF. No production migration, owner seed, SMTP delivery, frontend login cutover or deployment has been performed. See `docs/OWNER_IDENTITY_V2.md` for the backend contract and verification limits.

## Source-of-Truth Date

2026-10-24

## Owner Identity V2 — Current Scope

- Establish a new canonical Owner Registry seeded from the owner-provided Supabase owner UUID and primary email. Avoid embedding personal identifiers in this project-wide planning document; obtain actual values from approved owner-controlled configuration when implementing.
- Design new Owner Authentication rather than reusing the failing legacy login flow. Retain legacy components only until a verified migration/cutover, without treating them as the new identity authority.
- Record Supabase, Render, and Pollinations as separate provider accounts with provider-specific IDs, registration email, and evidence-based verification status. A shared email is a candidate matching attribute, not proof of cross-provider ownership.
- Do not require unrelated provider tables or sessions to share the same primary key. Link records only when a valid, verified relationship exists; otherwise keep their identifiers and verification separate.
- After implementation and verification, adapt dependent components to use Owner Identity V2 as their single source of truth. Do not switch production integrations or remove old authentication as part of this documentation change.
- Focus on owner records, identity verification, account relationships, and login integration. Wallet, budget, spending authorization, and provider execution are **out of scope for this initiative**; existing runtime safety controls remain unchanged.

## Current Gate

Review the isolated backend patch and offline evidence. Before activation, separately authorize staging verification of database collisions/permissions, PostgREST RPC integration, native multi-connection contention and SMTP delivery. Canonical owner seed confirmation and frontend/API cutover remain pending; no production change or login replacement is authorized by this status update.

## Completed milestones — 2026-10-28

- **Pollinations BYOP PR #212 — MERGED.** [PR #212](https://github.com/soloforge-ai/SoloForge-AI/pull/212) merged at `ad0cb4ea1b06677c19c6c82380ec97e9f121da59`. Live provider generation and spending remain disabled by default; merge is not production E2E proof.
- **Content Studio Phase 0 Exact Reuse & Quality Audit — COMPLETED.** Audited the merged main baseline and identified the smallest text-first extension of existing Content Factory jobs, review and UI contracts.

## Content Studio Phase 1 — IMPLEMENTED LOCALLY — VERIFICATION PENDING

- **13 changed files reported**, implementing the offline manual text-variant slice; **77 distinct backend tests passed** across affected offline runs.
- **Flutter analyze and tests: NOT RUN.** Flutter SDK unavailable locally.
- **Native PostgreSQL concurrency, actual Supabase RLS and production E2E: UNVERIFIED.** SQL/WASM and offline fixtures do not establish production behavior.
- **Local patch not committed or delivered to GitHub.** No production migration, live provider use, worker activation or publishing was performed.

Owner Identity V2 remains the active P0 initiative.

## Previous Initiative — Paused

**SoloForge State Reset / Content Factory E2E Proof Preparation** is paused by the owner's newer priority decision. The historical sequence, rationale, and evidence below are retained for traceability and are not instructions to execute while Owner Identity V2 is active.

---

## Why This Reset Exists

SoloForge implementation has advanced beyond the previous Product-to-Post documentation.

The repository now contains working foundations for content jobs, idea analysis, AI generation, asset generation, branding, TTS, final rendering, Publora publishing, analytics, Telegram workflows, Android APK builds, and Render production checks.

The immediate risk is no longer lack of features.

The immediate risk is that documentation, open branches, and end-to-end verification do not clearly identify what is production-ready versus merely implemented.

Therefore this cycle freezes feature expansion and performs a state reset before additional product growth.

---

## Active Sequence

The owner-approved sequence is:

### 1. Update Source of Truth

Synchronize the main project documents with the implementation state as of 2026-10-01.

Required state labels:

- **PRODUCTION / VERIFIED** — proven in the relevant production path
- **IMPLEMENTED / NEEDS E2E** — code exists but the complete production workflow is not yet proven
- **RETAINED** — working or reusable infrastructure retained without being the active roadmap driver
- **EXPERIMENTAL / OPEN PR** — not part of production `main`
- **FROZEN** — must not expand without owner approval

### 2. PR Cleanup

Review open pull requests and explicitly classify each as:

- MERGE
- CLOSE
- ARCHIVE
- KEEP

The purpose is to restore `main` as the single clear production baseline.

### 3. Content Factory E2E Proof

Run one real content idea through the actual workflow:

```text
Idea
→ Analyze / MiniBoss
→ AI Generate
→ Review
→ Approve
→ Asset Generation
→ SoloForge Branding
→ TTS / Final Render when required
→ Ready to Publish
→ Publora
→ Real Published Post
```

### 4. Idea #003 Validation Loop

Only after the Content Factory E2E path is green:

```text
Audience / Pain
→ Content
→ Lead Magnet
→ Lead Capture
→ Validation
→ Offer
→ Pre-sell
→ Build
→ Deliver
```

Core business rule:

> **Don't build inventory. Build validated offers.**

---

## Current Definition of Done

The current milestone is complete only when one real content job:

1. begins from a real idea inside SoloForge;
2. receives an analysis / MiniBoss decision;
3. produces usable AI-generated content;
4. is reviewable by the user;
5. is explicitly approved;
6. receives the required asset;
7. carries SoloForge branding;
8. completes audio/render stages when its route requires them;
9. reaches `READY_TO_PUBLISH`;
10. is submitted through Publora;
11. reaches a real publishing destination;
12. has traceable evidence for the major state transitions.

A component test or green CI job alone does not satisfy this Definition of Done.

---

## Verified / Retained Foundations on main

The following implementation foundations are present and should be preserved:

### Product / Discovery

- Product Catalog and discovery
- Feed Processor
- MiniBoss scoring and ranking
- Product Intelligence / Product Forge foundations

### Content Operations

- Content Job model and API
- idea analysis
- content-format recommendations
- review/edit/approve workflow
- content state management
- content analytics foundations
- performance ingestion / feedback foundations

### AI / Creative

- multi-provider text-generation infrastructure
- Asset Forge v1
- Pollinations image-generation infrastructure
- local asset fallback
- SoloForge AI visual branding
- Character Memory bridge used by Asset Forge
- output-quality processing

### Media

- Edge TTS integration
- audio worker
- subtitle generation
- final FFmpeg render
- Supabase media storage paths

### Publishing

- Publora publishing integration
- publishing-account validation
- publish-now / scheduling flow
- publish submission atomically claims `READY_TO_PUBLISH` jobs with no `publora_post_id` as `PUBLISHING` / `PENDING` before calling Publora; competing claims return HTTP 409 without submitting
- ambiguous submission outcomes remain `PUBLISHING` / `PENDING` with no post ID for manual reconciliation; do not reset or automatically retry these jobs
- publishing-status synchronization

### Platform / Delivery

- Flutter application
- FastAPI backend
- Render deployment blueprint
- Android APK GitHub Actions build
- Render production smoke workflow
- Supabase-backed runtime data
- retained Telegram integrations

---

## Implemented but Still Requires E2E Proof

Do not label the following as fully production-proven until the E2E milestone is complete:

- one continuous Idea → Publish workflow
- live text provider behavior within that exact tested workflow
- automatic progression through all required workers for one real job
- real Publora publication from the same job
- real platform publication confirmation
- performance feedback from the published result
- unattended 24/7 operation

---

## Known Current Risks

### 1. Documentation Drift

Previous documentation still described the early-September Product-to-Post / provider-qualification phase even though the repository had progressed substantially.

This State Reset corrects the human-maintained source of truth.

### 2. Open PR Drift

Multiple open pull requests represent alternative or unfinished directions.

They must not be assumed to be production merely because code exists in a branch.

### 3. Partial Verification

Current automated smoke coverage proves important backend / Asset Forge health but does not prove the full content production chain.

### 4. Media Quality Follow-up

Subtitle timing quality remains a known area of active/open work and must be judged separately from core state-machine correctness.

---

## Retained Completed Product

Asset Forge v1 remains **Working Product #1** after owner-accepted Android E2E evidence on 2026-09-04.

Its retained contract remains:

- 4 poses
- 1 AI generation
- local review / fix / export
- no automatic paid regeneration by default

Non-blocking visual polish must not reopen the whole product unless it blocks the active E2E path.

---

## Frozen / Not Active Roadmap Drivers

Do not expand unless the owner explicitly changes priority:

- Chat Prawtwan expansion
- Idea Flow / Telegram Idea Inbox expansion
- SoloForge Income Engine P2+
- new agent systems
- new memory systems
- billing
- unrelated product verticals
- broad architecture refactors

---

## Explicit Non-Goals Until E2E Is Green

Do not add:

- another content engine
- another AI provider solely for experimentation
- another social-publishing architecture
- new autonomous agents
- new product verticals
- broad UI polish
- billing
- large refactors

If an E2E failure exposes a blocker, fix the smallest blocker only.

---

## Architecture Rule

`docs/CURRENT_SPRINT.md` describes human-approved current development intent.

`docs/ROADMAP.md` describes human-approved product direction.

Project Scanner describes observable repository structure and implementation signals.

These concepts must remain separate.

---

Last updated: 2026-10-01 — SoloForge State Reset established. Active gate is Source of Truth → PR Cleanup → Content Factory E2E Proof → Idea #003 Validation Loop.

---

## Historical Task Board Archive (Superseded)

The following is the verbatim historical snapshot formerly stored in
`.ai/AI_TASK.md` (v1.8.0). It is retained **for traceability only**, not as
a current task list, authorization, or instruction to resume old initiatives.
The active priorities and owner approvals above take precedence.

````text
# SoloForge AI Task Board

Version: v1.8.0

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
- Project Scanner roadmap authority is separated from human product planning: scanner implementation suggestions belong in `tools/scanner/output/IMPLEMENTATION_ROADMAP.md`, while `docs/ROADMAP.md` is human-maintained product direction.

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
6. Read `docs/ROADMAP.md` for human-approved product direction when longer-horizon intent is relevant.
7. Prefer ACTIVE/current Product-to-Post decisions over superseded or frozen Income Engine direction.
8. Treat Asset Forge v1 as a retained component, not the active roadmap by default.
9. Do not restart Income Engine expansion, Chat Prawtwan expansion, Idea Flow expansion, or unrelated infrastructure without explicit owner approval.
10. Prefer the smallest change that advances the real Product-to-Post workflow.
11. Do not infer human intent from generated scanner output.

---

# Notes

Human-approved active development state lives in `docs/CURRENT_SPRINT.md`.

Human-approved product direction lives in `docs/ROADMAP.md`.

Generated scanner reports describe observed implementation and must not replace human sprint state or product direction.

Scanner-generated implementation roadmap output belongs in `tools/scanner/output/IMPLEMENTATION_ROADMAP.md`.

---

End of Task Board
````
