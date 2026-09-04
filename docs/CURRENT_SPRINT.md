# SoloForge AI Current Work

> Human-maintained source of truth for the active development cycle.
>
> This file MUST NOT be overwritten by Project Scanner output.

## Active Initiative

SoloForge Income Engine — P2 Opportunity Library v0

## Status

In Validation

## Previous Gate

P1 — Income Diagnostic v0: **PASS**

P1 validated 15 beginner-safe diagnostic questions against 10 deliberately different personas. It preserves evidence-backed capability, unknown-skill state, urgency, time, budget, devices, work preferences, public/customer interaction tolerance, assets, risk and market reach without recommending an income path.

Primary P1 spec:

`docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`

## P2 Goal

Define a controlled set of income opportunities before any personalized ranking engine exists.

Primary P2 spec:

`docs/INCOME_ENGINE_P2_OPPORTUNITY_LIBRARY.md`

## P2 Current Scope

- 28 meaningfully different income opportunities
- service, productized-service, operational, creative, technical, product and content/distribution models
- startup-cost bands
- time-to-first-revenue bands
- required capability signals
- device and customer/public-presence constraints
- recurring-revenue potential
- scalability
- AI leverage
- demand-evidence quality
- hard disqualifiers
- cheap validation experiment for each opportunity

## Market-Evidence Rule

P2 must not use free-form LLM popularity as market demand.

The v0 library uses current external evidence from Upwork 2026 hiring data, Fiverr 2026 marketplace-search trends, and the OECD 2026 D4SME survey. Evidence tags are directional only and do not guarantee demand, conversion, pricing or income.

## Locked Product Principle

SoloForge should reduce wrong experiments, not merely generate more ideas.

P2 does not answer:

> What are the best ways to make money online?

It prepares the controlled opportunity side of the later question:

> Given this person's actual constraints, evidence and market access, which income experiment is worth testing first?

## P2 Non-Goals

Do not add during P2:

- personalized opportunity ranking
- weighted scoring
- Flutter UI changes
- Supabase schema
- billing
- scraping automation
- autonomous agents
- paid AI generation
- income guarantees

## P2 Acceptance Gate

P2 passes only if:

- at least 20 distinct opportunities exist
- metadata is sufficient for later eligibility filtering and ranking
- service, product, content, operational and technical paths are represented
- urgent-income versus long-horizon paths are distinguishable
- customer/public-presence, device, budget and capability constraints are explicit
- distribution-dependent paths are not mislabeled as fast/predictable income
- each opportunity has a cheap validation experiment
- demand claims carry evidence-quality labels
- no personalized ranking occurs yet

## Completed Product Retained

Asset Forge v1 remains closed as Working Product #1.

Its contract remains 4 poses / 1 AI generation with local review/fix/export and no automatic additional Pollen. Residual light fringe remains tracked separately in GitHub Issue #48.

## Next Step

Validate P2 library completeness and constraint coverage. Do not start P3 scoring until P2 passes and the owner explicitly approves progression.

---

Last updated: 2026-09-04 — Income Engine P2 Opportunity Library v0 started.
