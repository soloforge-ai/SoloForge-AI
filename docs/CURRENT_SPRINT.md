# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Income Engine — P1 Income Diagnostic v0

## Status

In Validation

## Sprint Outcome

Define and validate the minimum diagnostic needed to understand a user's real income constraints, capabilities, urgency, work preferences, available assets, and uncertainty before any income path is recommended.

The P1 specification is maintained in:

`docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`

## P1 Scope

- 15 beginner-safe diagnostic questions
- normalized user profile output
- evidence/confidence requirements for inferred capability
- explicit fallback when the user does not know their own skills
- 10-persona validation gate
- P1 PASS/FAIL criteria

## P1 Non-Goals

Do not add during this phase:

- income-path recommendation
- Opportunity Library
- scoring/ranking engine
- Flutter UI changes
- Supabase schema
- billing
- scraping
- autonomous agents
- paid AI generation
- revenue guarantees

P1 must validate the diagnostic first. Recommendation work belongs to P2 and later phases only after P1 passes.

## Locked Product Principle

SoloForge should reduce wrong experiments, not merely generate more income ideas.

The diagnostic must preserve enough evidence and constraints for a later system to answer:

> Given this person's real situation, what is the highest-probability income experiment to test first?

## P1 Acceptance Gate

Run the same diagnostic against 10 deliberately different personas, including:

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

P1 passes only if the resulting normalized profiles differ meaningfully, unknown skills remain unknown, hard constraints are preserved, and inferred capability is traceable to evidence.

## Completed Product Retained

Asset Forge v1 remains closed as Working Product #1 after the owner-accepted Android E2E test on 2026-09-04.

Its default contract remains:

- 4 poses
- 1 AI generation
- local review/fix/export without automatic additional Pollen

Residual light fringe remains tracked separately as GitHub Issue #48 and does not reopen Asset Forge v1.

## Architecture Rule

Project Scanner describes observable repository structure and implementation signals.

This document describes human-approved current development intent.

These are different concepts and must remain separate.

## Next Step

Execute the P1 validation against 10 test personas. Do not implement P2, recommendation logic, or UI until the P1 acceptance gate is reviewed.

---

Last updated: 2026-09-04 — Income Engine P1 validation started.
