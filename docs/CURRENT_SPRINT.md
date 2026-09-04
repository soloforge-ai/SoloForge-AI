# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Income Engine — P4 Deterministic Recommendation Engine Prototype

## Status

Prototype Implemented — Automated Tests PASS / Calibration Review Required

## Completed Gates

- P1 — Income Diagnostic v0: **PASS**
- P2 — Opportunity Library v0: **PASS**
- P3 — Eligibility + Opportunity Scoring v0: **PASS (manual decision-model dry run)**
- P4 — Deterministic prototype: **13/13 local automated tests PASS**

## P4 Outcome

P4 converts the P1/P2/P3 decision model into executable Python without using an LLM for ranking.

Implemented files:

- `backend/income_engine.py`
- `backend/test_income_engine.py`

The prototype contains:

- 28 controlled P2 opportunity records
- P1-style evidence states: `PROVEN`, `SIGNAL`, `UNKNOWN`, `CONTRADICTED`
- hard eligibility before scoring
- device/budget/customer/public/capability/timing/distribution/schedule checks
- P3 weighted fit score
- confidence handling
- `RECOMMEND`, `TWO_WAY_TEST`, `DISCOVERY_REQUIRED`, `NO_CONFIDENT_MATCH`
- explanation fields and P2 cheap validation experiment output
- no dynamic opportunity generation
- no network/LLM dependency
- no persistence or UI integration

## P4 Automated Validation

Command used locally:

```text
cd backend
python -m unittest -v test_income_engine.py
```

Result:

```text
Ran 13 tests
OK
```

Coverage includes:

- 28 unique opportunity records
- all 10 P1 personas
- unknown-skill -> `DISCOVERY_REQUIRED`
- capital-without-execution -> `NO_CONFIDENT_MATCH`
- urgent users do not receive long-horizon distribution-dependent paths as primary defaults
- structured Fit Score + cheap experiment output

## Important Calibration Finding

Turning the P3 manual model into exact arithmetic exposed differences that were hidden during manual dry-run review.

The P3 contract says:

> if the top two eligible-primary scores differ by less than 5 points, return `TWO_WAY_TEST`.

The executable prototype correctly applies this rule. As a result, several personas that the P3 manual table loosely described as `RECOMMEND` resolve to `TWO_WAY_TEST` because the numeric score gap is actually below 5.

Examples from P4:

- data persona: O01 remains top, but nearby data paths are close enough for `TWO_WAY_TEST`
- speaker/sales persona: O07 remains top, but nearby candidates are within the tie threshold
- seller persona: O16 remains top, but O15/O05 are numerically close
- unemployed admin/support persona: O04 remains top, but O05 is close
- phone-only operations persona: O05 remains top, but O04/O23 are close enough to avoid false certainty

This is considered correct behavior under the explicit P3 tie rule, not a test failure.

A second calibration finding appears for the visual/product persona. Under the locked P3 weights, O13 Canva Social Design ranks above O26 Niche Digital Asset Packs because the short timing band and stronger current-demand evidence outweigh the user's product preference and the long/distribution-dependent structure of O26.

This does **not** mean O13 is proven to be better in the real world. It means the current numerical weights produce that result.

Therefore P4 should not be promoted into UI/production recommendation behavior until the owner reviews whether the current P3 weights and preference treatment reflect the intended product philosophy.

## Guardrails

P4 must not:

- call Fit Score a success probability
- promise income or timing
- generate new opportunities from LLM memory
- bypass hard eligibility
- convert tool familiarity into proven skill
- force a recommendation when evidence is weak
- add Flutter UI yet
- add Supabase persistence yet
- add billing or autonomous execution

## Completed Product Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking polish.

## Next Gate

Do **not** proceed directly to UI.

Review P4 calibration findings first:

1. keep the strict `<5 = TWO_WAY_TEST` tie rule or change it explicitly
2. decide whether explicit business-model preference should have more influence than the current 15-point Execution Fit component allows
3. after calibration is approved, rerun the 10-persona automated suite
4. only then consider P5 / UI integration or real-user validation

---

Last updated: 2026-09-04 — P4 deterministic prototype implemented; 13/13 automated tests PASS; calibration review required.
