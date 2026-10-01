# Reading Time

Estimated Reading Time

60 seconds

Purpose

Current Project Snapshot and Guardrails

Read Before

AI_RULES.md

AI_TASK.md

PROTOCOL.md

# SoloForge AI Context

Version: v1.5.0

---

# Project Overview

Project Name

SoloForge AI

Project Type

AI Creator Operating System

Mission

Build a commercial-grade AI platform that enables creators, affiliate marketers, and solo entrepreneurs to turn ideas, product data, and validated audience demand into useful content and digital business outputs with AI-assisted workflows.

---

# Current Development Status

Status

Active Development

Source-of-Truth Date

2026-10-01

Current Objective

**SoloForge State Reset — Content Factory E2E Proof**

The repository has progressed beyond the earlier Text Model Qualification / Product-to-Post preparation phase.

Current implementation now includes substantial content-operations infrastructure:

- idea analysis
- MiniBoss scoring
- content-format recommendations
- Content Jobs
- AI generation infrastructure
- review / edit / approval
- asset generation
- SoloForge branding
- TTS
- subtitle / final render
- Supabase-backed content state and media paths
- Publora publishing integration
- analytics / performance foundations
- Telegram-related retained workflows
- Android APK CI
- Render production smoke

The active engineering problem is no longer "add more capability."

The active engineering problem is:

> Prove that the existing capabilities form one reliable, traceable production workflow.

---

# Owner-Approved Active Sequence

The current order is mandatory unless the owner changes priority:

```text
1. Update Source of Truth
2. PR Cleanup
3. Content Factory E2E Proof
4. Idea #003 Validation Loop
```

Do not insert unrelated feature development between these stages.

---

# Current E2E Target

One real content idea must complete:

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

Required mindset:

- implementation is not the same as production proof
- a green component test is not the same as E2E proof
- an open PR is not production
- manual intervention is acceptable only where explicitly allowed by the current test plan
- fix the smallest blocker discovered by the E2E run

---

# Business Direction After E2E

After the content path is proven, the next approved initiative is:

**Idea #003 — Audience → Lead Magnet → Validation → Pre-sell → Product**

Workflow:

```text
Audience Problem
→ Content
→ Lead Magnet
→ Lead Capture
→ Validation
→ Offer
→ Pre-sell
→ Build
→ Deliver
→ Measure
```

Core principle:

> **Don't build inventory. Build validated offers.**

Thai rule:

> **อย่าผลิตของเพิ่มเพราะเราผลิตได้ — ผลิตเมื่อมีหลักฐานว่าคนต้องการ**

This validation loop is not active implementation work until the Content Factory E2E gate is green.

---

# Technology Stack

Frontend

- Flutter
- Dart

Backend

- Python
- FastAPI

Database / Persistence / Storage

- Supabase
- Firebase where retained / applicable
- local persistence for internal tools where appropriate

Deployment / CI

- Render
- GitHub Actions
- Android APK build workflow
- production smoke workflow

AI / Model Infrastructure

Implemented / available in repository:

- Pollinations
- Gemini-compatible generation / qualification path
- Groq-compatible generation path
- OpenRouter-compatible generation path
- text model qualification tooling

Do not infer that every provider is production-configured merely because adapter code exists.

Media

- Pillow
- Edge TTS
- FFmpeg

Publishing

- Publora integration

---

# Active / Retained Product Foundations

## Product and Discovery

- Product Feed / Feed Processor
- Product Catalog
- MiniBoss scoring and ranking
- Product Intelligence
- Product Forge foundations

## Content Operations

- idea intake / analysis
- content-format recommendations
- Content Job state model
- content generation
- review / edit / approval
- content asset generation
- analytics / performance ingestion
- performance feedback foundations

## Creative / Media

- Asset Forge v1
- Pollinations OAuth/session infrastructure
- Pollinations image-generation path
- local fallback generation
- output-quality processing
- Character Memory bridge used by Asset Forge runtime
- SoloForge branding
- TTS / audio generation
- subtitle / final rendering

## Publishing

- Publora account discovery / validation
- publish-now and scheduling integration
- publishing-status synchronization

## Platform

- Flutter application
- FastAPI backend
- Supabase runtime integration
- Android APK CI
- Render deployment / production smoke

---

# Status Classification Rules

Use the following labels consistently.

## PRODUCTION / VERIFIED

Use only when the relevant real workflow has been demonstrated with acceptable evidence.

## IMPLEMENTED / NEEDS E2E

Use when code exists and component tests may pass, but the complete production path has not yet been proven.

## RETAINED

Use for working or reusable systems that are preserved but are not the active roadmap driver.

## EXPERIMENTAL / OPEN PR

Use for branch work not intentionally accepted into production `main`.

## FROZEN

Use when work must not expand without explicit owner authorization.

Never upgrade status based on assumption.

---

# Current Production Evidence

Verified supporting evidence includes:

- Asset Forge v1 owner-accepted Android E2E evidence from 2026-09-04
- Android APK build workflow success on current development history
- Render production smoke checks
- backend / contract tests across content infrastructure

These do not yet prove the complete Content Factory Idea → Publish loop.

---

# Known Current Risks

## Documentation Drift

Previous project documentation lagged behind the implementation state.

This State Reset is intended to restore reliable human-maintained project truth.

## Open PR Drift

Several open PRs contain potentially useful or obsolete work.

Do not treat them as production.

They must be explicitly classified during PR Cleanup.

## E2E Gap

The current production smoke does not prove the full content pipeline.

The next engineering milestone is one real traceable Idea → Publish run.

## Media Quality Follow-up

Subtitle timing remains a known quality area and may require targeted work if it blocks acceptable E2E output.

---

# Completed Product Retained

Asset Forge v1 remains Working Product #1.

Retained default contract:

- 4 poses
- 1 AI generation
- local review / fix / export
- no automatic additional paid regeneration by default

Do not reopen the whole Asset Forge scope for non-blocking polish.

---

# Frozen Capabilities / Initiatives

The following may remain merged, documented, or preserved but are not active roadmap drivers:

- Chat Prawtwan expansion
- Idea Flow / Supabase-backed Telegram Idea Inbox expansion
- SoloForge Income Engine P2+
- new general-purpose agents
- new memory systems
- billing
- unrelated verticals
- broad architecture refactors

Do not expand them without explicit owner approval.

---

# Development Philosophy

Prioritize:

Useful business output

↓

End-to-end proof

↓

Correctness

↓

Consistency

↓

Maintainability

↓

Scalability

Prefer completion of a proven workflow over accumulation of subsystems.

---

# Documentation Authority

Human-approved current development intent:

`docs/CURRENT_SPRINT.md`

Human-approved product direction:

`docs/ROADMAP.md`

AI working context:

`.ai/AI_CONTEXT.md`

AI task board:

`.ai/AI_TASK.md`

Observed implementation:

Project Scanner output

Authority order:

1. Explicit owner instruction
2. `docs/CURRENT_SPRINT.md`
3. `docs/ROADMAP.md`
4. `.ai/AI_CONTEXT.md`
5. `.ai/AI_TASK.md`
6. scanner-generated observations

Project Scanner must not overwrite human product intent.

---

# Important Constraints

Always preserve project architecture.

Avoid unrelated modifications.

Do not rename existing folders without approval.

Do not rewrite completed systems unless the active E2E run proves a blocker.

Keep documentation synchronized with implementation.

Do not treat open PRs as production.

Do not treat code presence as proof of runtime configuration.

Do not add unrelated providers, agents, billing, memory, or product verticals during the State Reset.

Do not start Idea #003 implementation until the Content Factory E2E milestone is green.

---

# Current AI Responsibilities

Every AI assistant should:

- understand the State Reset sequence before acting
- preserve the existing architecture
- use `docs/CURRENT_SPRINT.md` as the primary active-state reference
- use `docs/ROADMAP.md` for approved sequencing
- distinguish implemented capability from production proof
- distinguish `main` from open PR work
- prefer the smallest fix required by evidence
- avoid feature expansion during E2E validation
- retain Asset Forge v1 unless a direct blocker is found
- keep Idea #003 queued behind the E2E gate

---

# Governing Questions

During State Reset:

> What is actually in production `main`, what is only implemented, and what is still branch work?

During E2E:

> Can one real idea enter SoloForge and leave as a real published post with traceable evidence?

After E2E:

> Can SoloForge turn content attention into qualified leads, validated offers, and revenue signals before building more inventory?

---

End of Context
