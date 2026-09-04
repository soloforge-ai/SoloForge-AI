# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Income Engine — P3 Eligibility + Opportunity Scoring v0

## Status

Validated — PASS

## Completed Gates

- P1 — Income Diagnostic v0: **PASS**
- P2 — Opportunity Library v0: **PASS**
- P3 — Eligibility + Opportunity Scoring v0: **PASS (manual decision-model dry run)**

## P3 Outcome

P3 now defines the deterministic decision contract that combines P1 user evidence with P2 opportunity metadata.

Primary P3 spec:

`docs/INCOME_ENGINE_P3_ELIGIBILITY_SCORING.md`

The decision order is locked as:

1. hard eligibility filters
2. capability uncertainty / verification state
3. weighted opportunity scoring
4. recommendation confidence
5. explanation of fit and rejection
6. P2 cheap validation experiment as the next action

## P3 Weighted Score

The v0 fit heuristic uses:

- Capability Fit — 25
- Revenue Timing Fit — 20
- Acquisition Reachability — 15
- Execution Fit — 15
- Market Evidence — 10
- Margin Profile — 5
- Recurring Revenue — 5
- Scalability — 3
- AI Leverage — 2

Total: 100

The score is a fit heuristic only. It is not success probability, expected revenue or an income guarantee.

## Decision States

Opportunity-level:
- `INELIGIBLE`
- `VERIFY_FIRST`
- `ELIGIBLE_PRIMARY`
- `ELIGIBLE_SECONDARY`

User-level:
- `RECOMMEND`
- `TWO_WAY_TEST`
- `DISCOVERY_REQUIRED`
- `NO_CONFIDENT_MATCH`

A valid no-match is preferred over a generic recommendation.

## Validation Result

**PASS**

The manual dry run used the same 10 P1 personas.

Key validation behaviors:
- data-oriented user -> spreadsheet/data service path
- speaking/sales user -> outreach/appointment-setting path
- visual low-interaction user -> digital asset/template path
- existing seller -> marketplace operations path
- unknown-skill beginner -> `DISCOVERY_REQUIRED`
- student with formatting evidence -> document/presentation service
- time-poor full-time worker -> fixed-scope asynchronous service rather than response-heavy work
- unemployed admin/support user -> operations/admin path
- capital-rich but time-poor user -> `NO_CONFIDENT_MATCH` rather than invented capability
- zero-budget high-effort user -> phone-compatible support/operations path

This validation confirms that the decision model can differentiate users, preserve hard constraints, account for distribution access, demote long-horizon paths for urgent users, and refuse to force a recommendation.

## Guardrails

P3 must not:
- generate new income opportunities dynamically
- interpret Fit Score as probability of success
- promote weak tool exposure to proven skill
- bypass hard eligibility with popularity/demand
- make income guarantees
- add Flutter UI
- add Supabase persistence
- add billing
- add autonomous execution

## Completed Product Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking polish.

## Next Candidate

`P4 — Deterministic Recommendation Engine Prototype`

P4 should encode P1/P2/P3 as machine-readable contracts, implement eligibility + scoring without free-form LLM ranking, and add automated fixtures for the 10 personas.

Do not start P4 until the owner explicitly approves progression.

---

Last updated: 2026-09-04 — Income Engine P3 decision-model validation PASS.
