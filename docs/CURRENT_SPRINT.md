# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Product-to-Post

## Current Implementation

Cleanup Scope Reset #1

## Status

In Progress

## Product Objective

Restore SoloForge to its original commercial workflow:

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

## Cleanup Scope Reset #1

This cleanup intentionally reduces the active product surface without rebuilding the application.

Approved scope:

- keep the product catalog, feed processor, MiniBoss ranking, Product Intelligence, Product Forge, and Content Engine active
- keep Asset Forge as a reusable creative/image-processing component
- keep shared Pollinations OAuth/session and Asset Forge Memory/output-quality dependencies
- remove Chat Prawtwan and Developer Tools entry points from the Home screen
- remove confirmed dead/legacy Flutter Product/Sticker/Test implementations
- keep backend Prawtwan and Idea Flow implementations unchanged in this cleanup
- do not refactor Asset Forge in this cleanup

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

Income Engine P1 remains historical validated work. `P2 — Opportunity Library v0` is not active and must not begin unless the owner explicitly re-authorizes it.

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

## Next Step After Cleanup

Audit the existing Product Forge end-to-end and close the smallest missing gaps required for a real `Product → Ready-to-Post` test.

Do not add new agents, memory systems, verticals, billing, autonomous posting, or unrelated infrastructure before that product loop is proven unless the owner explicitly changes priority.

---

Last updated: 2026-09-05 — Product-to-Post scope reset approved.
