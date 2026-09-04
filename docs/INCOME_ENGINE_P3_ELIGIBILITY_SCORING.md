# SoloForge Income Engine — P3 Eligibility + Opportunity Scoring v0

Status: Validated — PASS (manual decision-model dry run)

Date: 2026-09-04

## Purpose

P3 converts the evidence-backed user profile from P1 and the controlled opportunity metadata from P2 into a deterministic decision process that can answer:

> Which income experiment is worth testing first for this specific person?

P3 must not behave like a free-form LLM recommendation. It must eliminate impossible or clearly unsuitable options first, then score only the remaining candidates, reduce certainty when evidence is weak, explain why the top path fits, explain why tempting alternatives were rejected, and return no confident recommendation when the evidence is insufficient.

P3 is still a specification/validation phase. It does not add Flutter UI, Supabase schema, production recommendation APIs, autonomous execution, billing, or income guarantees.

## Inputs

P3 consumes two controlled inputs.

### P1 user profile

Required fields include:
- income_goal
- revenue_urgency
- available_time
- schedule_consistency
- starting_budget
- maximum_loss_tolerance
- devices
- internet_access
- tool_familiarity
- observed_skill_signals
- preferred_work_modes
- customer_interaction_tolerance
- camera_tolerance
- voice_tolerance
- existing_assets
- distribution_assets
- sales_model_preferences
- risk_tolerance
- speed_vs_scale_preference
- languages
- market_reach
- skill_confidence
- diagnostic_mode
- unknowns

Every inferred capability must retain P1 evidence and confidence.

### P2 opportunity record

Required canonical fields include:
- id
- name
- model_type
- buyer
- core_deliverable
- startup_cost_band
- time_to_first_revenue
- required_capabilities
- minimum_device
- customer_interaction
- public_presence
- acquisition_modes
- acquisition_difficulty
- margin_profile
- recurring_revenue_potential
- scalability
- ai_leverage
- market_demand_signal
- evidence_level
- hard_disqualifiers
- cheap_validation_experiment

P3 must never generate new opportunity metadata on the fly.

## Decision States

P3 can return these opportunity-level states:

- `INELIGIBLE` — violates a hard user constraint.
- `VERIFY_FIRST` — potentially relevant, but required capability evidence is too weak to rank safely.
- `ELIGIBLE_PRIMARY` — can participate in the primary ranking.
- `ELIGIBLE_SECONDARY` — possible, but should not be the main recommendation because of timing/distribution/fit mismatch.

P3 final user-level states:

- `RECOMMEND` — one path is sufficiently strong to test first.
- `TWO_WAY_TEST` — top candidates are too close to force a single winner.
- `DISCOVERY_REQUIRED` — user capability is too uncertain; run skill discovery before recommending a path.
- `NO_CONFIDENT_MATCH` — current library contains no sufficiently supported primary path.

A valid no-match is better than a generic recommendation.

## Stage 1 — Hard Eligibility

Hard eligibility runs before any weighted score.

### E01 — Device eligibility

Reject when the opportunity requires a device the user cannot access.

Examples:
- `computer_required` + phone-only user -> `INELIGIBLE`
- `production_capable_device` + device cannot support required production workflow -> `INELIGIBLE`

`computer_preferred` is not a hard rejection if the task can reasonably be validated on the available device, but it reduces execution fit.

### E02 — Budget eligibility

Map P2 startup cost bands to maximum acceptable startup spend:

- `zero` -> THB 0 incremental required
- `very_low` -> normally <= THB 500
- `low` -> normally <= THB 2,000
- `moderate` -> normally <= THB 10,000
- `capital_required` -> above the moderate band or materially inventory/ad-spend dependent

If the opportunity's minimum plausible cost exceeds both the user's starting budget and maximum acceptable loss, mark `INELIGIBLE`.

These are heuristic bands, not promised costs.

### E03 — Public-presence eligibility

- `none` -> always compatible with camera/voice preference.
- `voice_optional` -> voice refusal does not reject; it reduces execution fit only if the practical variant would benefit from voice.
- `camera_optional` -> camera refusal does not reject; score the non-camera variant.
- `camera_preferred` -> camera refusal normally demotes to `ELIGIBLE_SECONDARY`; reject only if the specific validation variant actually requires personal on-camera presence.

### E04 — Customer-interaction eligibility

- opportunity `high` + user interaction tolerance `low` -> `INELIGIBLE`
- opportunity `high` + user tolerance `medium` -> eligible with penalty
- opportunity `medium` + user tolerance `low` -> eligible with penalty unless a P2 hard disqualifier says otherwise

### E05 — Capability contradiction

If P1 evidence directly contradicts a required capability or a P2 hard disqualifier is clearly triggered, mark `INELIGIBLE`.

Examples:
- professional translation + weak target-language proficiency
- complex dashboard work + no computer
- response-sensitive support + inability to maintain response windows

### E06 — Capability uncertainty

Required capability evidence uses these P3 match states:

- `PROVEN` — direct work, portfolio, repeated behavioral evidence
- `SIGNAL` — related behavior or tool use supports the capability but does not prove it
- `UNKNOWN` — no usable evidence
- `CONTRADICTED` — evidence indicates poor fit or explicit inability

Numerical capability values for scoring:
- PROVEN = 100
- SIGNAL = 65
- UNKNOWN = 25
- CONTRADICTED = 0

If `diagnostic_mode = skill_discovery` and no opportunity reaches a capability-fit average of at least 50 from real evidence, P3 returns `DISCOVERY_REQUIRED` rather than choosing a business model.

If a higher-skill opportunity depends on mostly UNKNOWN capabilities, mark that opportunity `VERIFY_FIRST`.

### E07 — Revenue timing eligibility

Revenue urgency does not mean SoloForge can guarantee timing. It controls whether a path is suitable as a primary experiment.

Timing-fit matrix:

| User urgency | fast | short | medium | long |
| --- | ---: | ---: | ---: | ---: |
| within 7 days | 100 | 65 | 20 | 0 |
| within 30 days | 95 | 100 | 50 | 10 |
| within 3 months | 85 | 95 | 100 | 50 |
| >3 months acceptable | 70 | 85 | 95 | 100 |

Additional primary-path rule:
- `long` cannot be a primary recommendation when the user needs money within 30 days.
- `medium` cannot be a primary recommendation when the user needs money within 7 days.

Such paths may remain `ELIGIBLE_SECONDARY` if other constraints fit.

### E08 — Distribution dependency

If `market_demand_signal = distribution_dependent` and the user needs income within 30 days:
- with no owned audience, platform traction, customer base, or relevant distribution asset -> `ELIGIBLE_SECONDARY` at best
- with proven distribution -> may remain `ELIGIBLE_PRIMARY`

This prevents Affiliate Content, creator channels, and similar paths from becoming generic urgent-income recommendations.

### E09 — Schedule compatibility

If an opportunity has `customer_interaction = high` and the user's schedule is highly inconsistent or too limited for response-sensitive work, reject or demote based on the P2 hard disqualifier and validation scope.

This rule preserves P1 availability as a real constraint instead of treating motivation as unlimited execution capacity.

## Stage 2 — Weighted Opportunity Score

Only `ELIGIBLE_PRIMARY` opportunities participate in the primary ranking.

`ELIGIBLE_SECONDARY` opportunities are scored separately and cannot outrank a valid primary candidate.

The P3 score is a **fit heuristic**, not a probability of success, expected income, or guaranteed conversion rate.

### Weights

| Component | Weight |
| --- | ---: |
| Capability Fit | 25 |
| Revenue Timing Fit | 20 |
| Acquisition Reachability | 15 |
| Execution Fit | 15 |
| Market Evidence | 10 |
| Margin Profile | 5 |
| Recurring Revenue | 5 |
| Scalability | 3 |
| AI Leverage | 2 |
| **Total** | **100** |

### S1 — Capability Fit (25)

Compute the average P3 capability value across P2 `required_capabilities` using traceable P1 evidence.

Rules:
- do not promote tool familiarity to PROVEN skill by itself
- weak/unknown skill evidence reduces this component
- `skill_confidence = low` caps Capability Fit at 45 until skill discovery produces evidence

### S2 — Revenue Timing Fit (20)

Use the E07 matrix above and normalize to the 20-point component.

This score expresses structural timing fit only. It must never be phrased as a promise that revenue will arrive within the band.

### S3 — Acquisition Reachability (15)

Base score by `acquisition_difficulty`:
- low = 80
- medium = 60
- high = 40

Add distribution advantage when P1 assets overlap P2 `acquisition_modes`:
- +20: direct proven overlap such as existing customers/audience/community/network matching the acquisition mode
- +15: relevant professional/local/community access
- +10: platform familiarity or credible channel access without proven audience
- +0: no relevant access

Cap at 100.

Examples:
- existing marketplace seller + `ecommerce_community` / `professional_network` -> strong boost
- no audience + algorithmic distribution -> no boost
- professional network + B2B direct outreach -> meaningful boost

### S4 — Execution Fit (15)

Execution Fit combines four sub-factors equally unless a hard rule already rejected the opportunity:

1. work-mode fit
2. customer-interaction fit
3. public-presence fit
4. business-model/schedule fit

Suggested sub-factor values:
- strong fit = 100
- acceptable = 75
- uncertain/not sure = 60
- weak fit = 35
- explicit aversion = 0

Do not double-count a hard mismatch that already caused `INELIGIBLE`.

### S5 — Market Evidence (10)

P2 demand signal + evidence level map:
- `current_growth` + `A` = 100
- `durable_workflow` + `B` = 75
- `distribution_dependent` + `C` = 45

If a future P2 record has a different valid pairing, use the lower of the demand-signal confidence and evidence-level confidence rather than inflating the score.

Market Evidence is directional only.

### S6 — Margin Profile (5)

- high = 100
- medium = 70
- low = 40

This reflects structural direct-delivery costs only and excludes the user's labor/time.

### S7 — Recurring Revenue (5)

- high = 100
- medium = 65
- low = 35

### S8 — Scalability (3)

- high = 100
- medium = 65
- low = 35

### S9 — AI Leverage (2)

- core = 100
- strong = 80
- assistive = 50

AI leverage is deliberately low-weighted. SoloForge must recommend the best economic experiment for the person, not the opportunity that sounds most AI-native.

## Score Interpretation

- `>= 75` — strong candidate for a first experiment if confidence is not low
- `65–74.9` — testable candidate; recommend carefully
- `55–64.9` — weak candidate; normally verify capability or compare alternatives first
- `< 55` — do not present as the primary recommendation

Additional rule:
- if top two eligible-primary scores differ by less than 5 points, return `TWO_WAY_TEST` instead of pretending the #1 result is meaningfully superior

## Stage 3 — Recommendation Confidence

Fit Score and Confidence are separate concepts.

### HIGH confidence

Requires all of:
- top score >= 75
- capability evidence is mostly PROVEN/SIGNAL
- no unresolved critical unknown
- no hard constraint is close to failure
- opportunity evidence level is A or B
- acquisition route has at least one realistic channel or is structurally low difficulty
- top-vs-second score gap >= 8

### MEDIUM confidence

Requires:
- score >= 65
- no unresolved hard contradiction
- capability evidence is sufficient for a cheap validation experiment

### LOW confidence

Examples:
- capability evidence mostly UNKNOWN
- only distribution-dependent opportunities fit an urgent user
- no realistic acquisition route is available
- score < 65
- several critical assumptions remain unresolved

LOW confidence cannot produce `RECOMMEND`. Use `DISCOVERY_REQUIRED`, `VERIFY_FIRST`, `TWO_WAY_TEST`, or `NO_CONFIDENT_MATCH`.

## Stage 4 — Explanation Contract

A recommendation must show evidence, not just a number.

Required output shape:

```text
decision_state
primary_opportunity
fit_score
recommendation_confidence
why_it_fits[]
constraints_checked[]
assumptions[]
alternatives[]
rejected_or_demoted[]
first_validation_experiment
```

### Explanation rules

`why_it_fits` must cite P1 evidence and P2 metadata.

Good:
> Spreadsheet Data Cleanup ranks highly because the user has repeated spreadsheet-help evidence, owns a Windows computer, needs income within 30 days, and the opportunity is zero-cost with a fast timing band.

Bad:
> You seem like a data person, so this is probably right for you.

`rejected_or_demoted` must explain tempting alternatives using the user's constraints.

Example:
> Affiliate Content was demoted because the user needs income within 30 days and has no existing audience/distribution asset; P2 classifies the path as distribution-dependent.

## Stage 5 — Cheap Experiment

P3 does not invent a large business plan.

For the selected opportunity, return the P2 `cheap_validation_experiment` as the next action.

The purpose is to generate market evidence cheaply before the user commits significant time or money.

Future phases may operationalize the experiment into tasks, but P3 does not automate execution.

## No-Match Behavior

SoloForge must be allowed to say:

> We do not have enough evidence to recommend a path yet.

This is required in two important cases:

1. `DISCOVERY_REQUIRED` — user does not know their skill and P1 evidence is too weak.
2. `NO_CONFIDENT_MATCH` — current P2 library does not contain a sufficiently suitable path.

P3 must never fill a gap by generating a new popular income idea from LLM memory.

## Manual Validation — 10 P1 Personas

Validation objective: confirm that P3 produces differentiated decisions, respects hard constraints, and can refuse to force a recommendation.

No result below is a revenue guarantee. The dry run validates decision behavior only.

| Persona | Expected P3 result | Primary / next state | Why |
| --- | --- | --- | --- |
| 1. Data / spreadsheet oriented | RECOMMEND | O01 Spreadsheet Data Cleanup | proven spreadsheet evidence, computer, low budget, 30-day urgency, fast zero-cost path |
| 2. Strong speaker + social familiarity | RECOMMEND | O07 Outreach / Appointment Setting Support | high interaction tolerance, speaking/selling signal, phone-compatible, service model, direct execution fit |
| 3. Visual creator, low customer interaction | RECOMMEND or TWO_WAY_TEST | O26 Niche Digital Asset Packs vs O25 Digital Templates | strong visual evidence, low interaction preference, product preference, 3-month horizon accepts slower distribution-dependent validation |
| 4. Existing small seller | RECOMMEND | O16 Marketplace Store Operations Support | proven store operations, existing marketplace/customer access, high interaction tolerance, recurring-service structure |
| 5. Beginner, no identified skill | DISCOVERY_REQUIRED | no forced opportunity | P1 intentionally contains no strong capability evidence; generic affiliate/content recommendation is prohibited |
| 6. Student, low budget | RECOMMEND | O08 Presentation & Document Formatting | repeated slide/formatting evidence, low startup cost, education-community access, no camera requirement |
| 7. Full-time worker, little time | RECOMMEND carefully | O08 Presentation & Document Formatting | evidence-backed fixed-scope asynchronous work fits better than response-sensitive support or daily content production |
| 8. Unemployed, substantial time, admin/support history | RECOMMEND | O04 Virtual Admin / Operations Assistant | admin evidence, laptop, high interaction tolerance, large time availability; timing remains a warning because P2 band is short rather than fast |
| 9. Money available, very little time | NO_CONFIDENT_MATCH | no forced opportunity | capital alone is not treated as execution skill; current library lacks a high-confidence path that matches 3 hours/week without inventing capability |
| 10. Almost no money, high willingness to work | RECOMMEND carefully | O05 Customer Support / Inbox Management | phone-compatible, zero startup cost, operational evidence, medium-high interaction tolerance, high time capacity; short timing band means no 7-day promise |

## Validation Findings

### V1 — Recommendations do not collapse to one generic path

PASS.

The expected outputs span data service, sales support, digital-product creation, ecommerce operations, document service, admin/support work, skill discovery, and no-match states.

### V2 — Urgent users are not pushed toward long-horizon audience businesses

PASS.

Distribution-dependent paths such as Affiliate Content and Faceless YouTube cannot become urgent-income defaults without proven distribution.

### V3 — Unknown skill remains unknown

PASS.

Persona 5 returns `DISCOVERY_REQUIRED` instead of an invented skill or generic beginner business.

### V4 — Capital is not confused with capability

PASS.

Persona 9 returns `NO_CONFIDENT_MATCH` rather than assuming available money makes technical, ecommerce, content, or investment-like execution suitable.

### V5 — Existing distribution assets matter

PASS.

Persona 4 benefits from marketplace/customer access while Persona 3/5 do not receive the same acquisition advantage.

### V6 — Hard constraints run before popularity

PASS.

Device, interaction, public-presence, capability, budget, timing and distribution rules can eliminate or demote paths before the weighted score.

### V7 — The model can explain rejection

PASS.

Every exclusion/demotion must be tied to a P1 constraint or canonical P2 field rather than opaque LLM reasoning.

## P3 Acceptance Gate

P3 passes when:

- hard eligibility executes conceptually before ranking
- weighted score uses only P1/P2 controlled fields
- unknown capability reduces confidence instead of being invented
- urgent users do not default to long-horizon distribution paths
- acquisition reachability accounts for the user's real assets
- fit score is clearly separated from success probability
- top-score ties can return TWO_WAY_TEST
- weak evidence can return DISCOVERY_REQUIRED or NO_CONFIDENT_MATCH
- explanations cite user evidence and opportunity metadata
- the selected next action is the cheap P2 validation experiment
- no new income opportunity is generated dynamically
- no income guarantee is made

## P3 Validation Conclusion

**P3 PASS — decision-model specification and manual 10-persona dry run**

This PASS validates the logic contract, not production implementation and not real-world revenue outcomes.

The next phase should not immediately build a large UI. The highest-value next step is a small deterministic implementation/test harness that encodes P1 profiles, P2 canonical opportunities, P3 eligibility rules and scoring, then checks that the 10 persona cases produce stable outputs.

## Handoff Candidate

Next candidate phase:

`P4 — Deterministic Recommendation Engine Prototype`

P4 should:
- encode P1/P2/P3 as machine-readable contracts
- implement eligibility and scoring without free-form LLM ranking
- add automated test fixtures for the 10 personas
- return structured recommendation/no-match output
- remain local/testable before adding Flutter UI or production persistence

P4 must not start until the owner explicitly approves progression.

## Locked Product Principle

SoloForge is not trying to answer:

> What are the best ways to make money online?

It is building toward:

> Given this person's real constraints, evidence, capabilities and market access, which income experiment is most worth testing first — and what should they avoid wasting time on?