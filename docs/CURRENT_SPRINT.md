# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

Pollen Demo MVP — Scope-Locked Delivery

## Status

In Progress

## Sprint Outcome

A user can connect Pollinations, generate one four-sticker pack, preview the
generated sheet, and download the ZIP without automatic retries or additional
pack-size scope.

## Locked Acceptance Criteria

- Production demo opens successfully.
- Pollinations connection can be initiated.
- OAuth callback establishes a usable session.
- The user can submit the sticker prompt inputs.
- Generation is locked to a 2x2 pack of four stickers.
- The generated sheet is shown as a preview.
- The resulting ZIP can be downloaded or shared.

## Scope Guard

This sprint must not add pack sizes above four, semantic subject detection,
video or audio generation, SoloForge billing, general authentication, history,
or unrelated refactors. New findings are recorded as backlog unless they block
an acceptance criterion, risk credentials, spend Pollen without a result, or
break production/download behavior.

## Previous Foundation Verification

Runtime verification completed successfully on Windows with Python 3.12.

```text
Ran 12 tests in 0.183s
OK
```

Verified capabilities:

- Decision Memory storage and retrieval
- ACTIVE → SUPERSEDED lifecycle without deleting history
- owner authority protection for authoritative decisions
- scoped parallel decisions
- JSON persistence
- append-only Memory Events
- event filtering and retrieval
- Decision → image generation → runtime event end-to-end flow
- superseded decisions preserve runtime history

## Completed Scope

- Normalized project state sources of truth
- Preserved human-maintained current work separately from generated scanner reports
- Approved Memory Foundation v1 specification
- Implemented Decision Memory MVP
- Implemented Version / Status lifecycle semantics
- Implemented Memory Event MVP
- Implemented basic retrieval behavior
- Integrated first runtime producer with image generation events
- Added runtime test runner
- Added end-to-end Memory Foundation tests
- Verified all 12 tests successfully

## Architecture Rule

Project Scanner describes observable repository structure and implementation signals.

This document describes human-approved current development intent.

These are different concepts and must remain separate.

## Out of Scope Retained for Future Evaluation

- Vector DB
- Graph DB
- autonomous memory deletion
- embeddings as a required dependency
- 3D brain visualization
- nightly consolidation / dreaming

## Next Step

Complete and verify the Pollen Demo MVP on `feature/pollen-demo-mvp`. Stop after
the locked acceptance criteria pass and request owner approval before a live
Pollen generation or production deployment.

---

Last updated for the scope-locked Pollen Demo MVP sprint.
