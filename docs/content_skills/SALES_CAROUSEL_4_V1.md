# SALES_CAROUSEL_4_V1 — Draft P0/P1

**Status:** Offline foundation only; not wired to Content Job APIs, Pollinations, worker, Supabase, or production.

## Intent
Owner-approved four-slide commercial portfolio workflow, separate from the existing five-slide signature design contract and SHORT_EDUCATIONAL_V1 skill. OUKU OK02 is a **reference-only pilot** until product identity, reuse rights and approved copy are verified.

Flow planned: product assets -> manual image-role review -> deterministic four-slide plan -> owner generation approval and cost quote -> future atomic claim -> future Pollinations image executor -> native Thai ASH carousel renderer -> commercial QA -> owner export.

P0 implementation:
- `backend/asset_forge/backend/carousel_policy_v1.py` is an importable **fail-closed** offline preflight prototype.
- Known Quest model choices are an **unverified snapshot**, not live pricing/capability proof. Model exact IDs, balances, pricing and reference-edit support require live validation when executor integration is designed.
- Paid, unknown, absent verified approval, unknown price, missing atomic claim, and executor-disabled all block.
- An approval fingerprint is *not* proof of identity; a future authenticated server must issue and verify it.
- Current preflight **always blocks** generation. No possibility of Pollen spending, no automatic retry or publish.
- Future implementation must use a persistent atomic claim, immutable request snapshots, audit trails, idempotency, ambiguous-timeout reconciliation, no retry, true spend reconciliation, and an authenticated owner approval store. A simple Boolean must not be trusted from a client.

P1 implementation:
- `backend/asset_forge/backend/sales_carousel_skill_v1.py` builds a deterministic review-only 4:5 (1080x1350) plan with HERO / FEATURES / USAGE / CTA, reference hashes, and ASH palette.
- Does not call models, generate images, render typography, or validate commercial rights.
- Claims and prices need independent human verification; do not promote merely because provided in the input.
- CEO can appear only with approved canonical master reference when necessary. Product shape and proportions are higher priority than stylistic prompting.

## Test scope
`pytest backend/asset_forge/tests/test_carousel_policy_v1.py`

Tests exercise fail-closed behavior, Quest/Paid separation, unverified quotes, budget limit, approval binding, four-slide output, and absent reference. CI and end-to-end checks are pending.

## Deliberately untouched
Production workers, Content Jobs workflow, current Publish/Publora claim logic, OAuth, image provider, existing Skill Router, database schema, all existing content templates. Draft PR only, do not merge/deploy without further approval.
