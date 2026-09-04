# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Income Engine — P4 Deterministic Recommendation Engine Prototype

## Status

Calibration Implemented — Preference / Revenue Tradeoff Policy Locked

## Completed Gates

- P1 — Income Diagnostic v0: **PASS**
- P2 — Opportunity Library v0: **PASS**
- P3 — Eligibility + Opportunity Scoring v0: **PASS (manual decision-model dry run)**
- P4 baseline deterministic prototype: **13/13 local automated tests PASS before calibration layer**

## P4 Baseline Outcome

P4 converts the P1/P2/P3 decision model into executable Python without using an LLM for ranking.

Baseline files:

- `backend/income_engine.py`
- `backend/test_income_engine.py`

The baseline prototype contains:

- 28 controlled P2 opportunity records
- P1-style evidence states: `PROVEN`, `SIGNAL`, `UNKNOWN`, `CONTRADICTED`
- hard eligibility before scoring
- device/budget/customer/public/capability/timing/distribution/schedule checks
- P3 weighted Fit Score
- confidence handling
- `RECOMMEND`, `TWO_WAY_TEST`, `DISCOVERY_REQUIRED`, `NO_CONFIDENT_MATCH`
- explanation fields and P2 cheap validation experiment output
- no dynamic opportunity generation
- no network/LLM dependency
- no persistence or UI integration

## Owner Product Decision — Preference First, Tradeoff Visible, User Decides

The owner has locked this product principle:

> Give meaningful weight to what the user actually wants to do. If the preferred path conflicts with a structurally faster or stronger revenue path, explain the difference clearly and let the user decide whether to optimize for preferred work or faster revenue validation.

SoloForge must **not** silently override an explicit preference merely because another path scores higher economically.

SoloForge must also **not** hide material economic tradeoffs merely to agree with the user.

The calibrated decision policy is:

`Preference First -> Show Tradeoff -> User Chooses`

## P4 Calibration Layer

Added:

- `backend/income_engine_choice.py`
- `backend/test_income_engine_choice.py`

The choice layer wraps the deterministic baseline engine rather than replacing it. This preserves P3 hard eligibility, scoring, confidence and no-match behavior while separating the final user-choice policy from the scoring model.

### New decision state

`TRADEOFF_CHOICE`

This state is returned when:

1. the user has an explicit business-model preference
2. an eligible path exists that matches that preference
3. a different eligible path ranks higher overall
4. the higher-ranked path has a visible structural advantage in revenue timing, acquisition reachability, or market evidence

When `TRADEOFF_CHOICE` is returned, SoloForge does **not** select a primary opportunity automatically.

Instead it exposes two options:

- `PREFERENCE_PATH` — the best eligible path matching what the user wants to do
- `REVENUE_PRIORITY_PATH` — the stronger practical/revenue-structure path under the current scoring model

Each option exposes:

- opportunity ID and name
- model type
- Fit Score
- time-to-first-revenue band
- capability fit
- revenue timing fit
- acquisition reachability
- execution fit
- market evidence
- first cheap validation experiment

The comparison must explicitly state that timing bands are structural heuristics, not income promises.

## Example — Visual / Product Persona

Before calibration, the baseline engine ranked:

- O13 Canva Social Design above
- O26 Niche Digital Asset Packs

because O13 has a shorter revenue-timing band and stronger current market evidence, even though O26 better matches the user's explicit `product` preference and desired working style.

Under the calibrated policy, SoloForge should not force O13.

It should return `TRADEOFF_CHOICE` and show:

### Preference Path

O26 — Niche Digital Asset Packs

Strengths:
- matches explicit product preference
- stronger execution fit for the desired work model
- stronger scalability structure

Tradeoffs:
- long time-to-first-revenue band
- distribution-dependent
- weaker current market evidence

### Revenue Priority Path

O13 — Canva Social Design

Strengths:
- short time-to-first-revenue band
- stronger current market evidence
- stronger recurring-service structure

Tradeoffs:
- service model does not match the user's explicit product preference
- requires more direct customer/client work

The user must choose which objective matters more now.

## Guardrails

The calibration layer must not:

- override `INELIGIBLE`
- override `DISCOVERY_REQUIRED`
- override `NO_CONFIDENT_MATCH`
- present revenue timing as a guarantee
- claim the higher economic score will definitely earn more
- hide the user's stated preference
- force the user into the economically stronger path
- dynamically generate new opportunities
- use LLM ranking
- add Flutter UI yet
- add Supabase persistence yet
- add billing or autonomous execution

## Test Coverage Added

`backend/test_income_engine_choice.py` covers:

- visual/product persona returns `TRADEOFF_CHOICE`
- O26 is exposed as `PREFERENCE_PATH`
- O13 is exposed as `REVENUE_PRIORITY_PATH`
- structural timing / execution / market differences are visible
- a matching preference preserves the normal baseline decision
- `DISCOVERY_REQUIRED` is never overridden
- `NO_CONFIDENT_MATCH` is never overridden

CI has **not** been checked for this calibration change. Follow the repository CI policy: check only when the owner explicitly requests it.

## Completed Product Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking polish.

## Next Gate

Before P5 / UI integration:

1. review the calibrated output shape with the owner
2. run/check automated tests when explicitly requested
3. confirm the wording for the two choices is understandable to non-technical users
4. only then expose this decision in a UI or real-user validation flow

---

Last updated: 2026-09-04 — P4 preference/revenue tradeoff calibration implemented; owner choice policy locked.
