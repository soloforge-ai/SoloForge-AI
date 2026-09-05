# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Product-to-Post

## Current Implementation

Text Model Qualification + Product-to-Post E2E Preparation

## Status

In Progress

## Product Objective

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

The immediate product goal is to complete this workflow for one real product before expanding architecture or adding unrelated verticals.

## Completed In This Cycle

### Cleanup Scope Reset #1

Merged and complete.

The active product surface is intentionally narrowed to Product-to-Post while retaining reusable shared infrastructure.

Retained active foundations:

- Product Catalog and discovery
- Feed Processor and MiniBoss
- Product Intelligence and Product Forge
- Content Engine
- Asset Forge as a reusable creative/image-processing component
- Pollinations OAuth/session infrastructure required by Asset Forge
- Asset Forge Character Memory and output-quality runtime dependencies

Chat Prawtwan and Developer Tools entry points were removed from Home, and confirmed dead/legacy Flutter Product/Sticker/Test implementations were removed.

### Text Model Qualification Harness

Merged and complete as isolated qualification infrastructure.

It can compare supported text providers against one Product-to-Post output contract without changing the production ContentEngine provider automatically.

### Live Text Qualification Runner

Merged and available for manual live qualification runs through GitHub Actions.

A successful workflow run is not, by itself, a provider approval. Qualification evidence must be judged from the generated report and the owner remains the final production gate.

## Current Gate

1. Obtain a usable live text-model qualification result.
2. Do not switch the production ContentEngine provider until the owner explicitly approves a qualified provider.
3. Inspect the existing Product Forge path and identify only the smallest missing gaps required for one real Product-to-Post E2E run.
4. Run one real product through the complete workflow and verify the result is useful, reviewable, and manually exportable/postable.

## Product Definition of Done

The next product milestone must demonstrate one real product completing the active path:

1. Product data is available in SoloForge.
2. The product is evaluated.
3. SoloForge provides useful selling-angle guidance.
4. Creative output is generated or prepared.
5. Caption/content is generated.
6. The user can review the result.
7. The result can be exported and posted manually.

Manual steps are acceptable until the end-to-end business workflow is proven.

## Frozen Initiatives

The following merged/completed capabilities are retained but are not active roadmap drivers:

- Chat Prawtwan MVP
- Idea Flow / Telegram Idea Inbox
- SoloForge Income Engine P1

Income Engine P1 remains historical validated work. `P2 — Opportunity Library v0` and later Income Engine expansion are not active and must not proceed unless the owner explicitly re-authorizes them.

## Completed Product Retained

Asset Forge v1 remains Working Product #1 after owner-accepted Android E2E evidence on 2026-09-04.

Its default contract remains:

- 4 poses
- 1 AI generation
- local review/fix/export without automatic additional Pollen

Residual light fringe remains tracked separately as GitHub Issue #48 and does not reopen Asset Forge v1 by default.

## Architecture Rule

Project Scanner describes observable repository structure and implementation signals.

This document describes human-approved current development intent.

These are different concepts and must remain separate.

## Explicit Non-Goals For The Active Gate

Do not add or expand:

- new agents
- new memory systems
- billing
- autonomous posting
- unrelated product verticals
- broad architecture refactors

unless the owner explicitly changes priority.

---

Last updated: 2026-09-05 — Cleanup #1, Text Model Qualification Harness, and Live Qualification Runner are merged; active gate is provider qualification followed by one real Product-to-Post E2E run.
