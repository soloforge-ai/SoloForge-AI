# SoloForge AI Task Board

Version: v1.7.0

---

# Current Work

Title

SoloForge Income Engine — P2 Opportunity Library v0

Status

Validated — PASS

Primary Specs

- `docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`
- `docs/INCOME_ENGINE_P2_OPPORTUNITY_LIBRARY.md`

---

# Completed Gates

P1 — Income Diagnostic v0: **PASS**

P2 — Opportunity Library v0: **PASS**

---

# P2 Goal Achieved

SoloForge now has a controlled opportunity library that later eligibility/ranking logic can evaluate against P1 profiles without relying on free-form LLM popularity guesses.

The library contains 28 distinct opportunities across service, productized service, operational, creative, technical implementation, digital product, content and platform-work models.

---

# P2 Canonical Metadata

Every opportunity now provides:

- startup cost
- time to first revenue
- required capabilities
- minimum device
- customer interaction
- public presence
- acquisition modes
- acquisition difficulty
- structural margin profile
- recurring revenue potential
- scalability
- AI leverage
- market-demand signal
- evidence level
- hard disqualifiers
- cheap validation experiment

Scalar metadata uses canonical single-value enums. Mixed values such as `fast-short`, `medium-high`, `zero-very_low`, and `A/B` are not allowed in the canonical P2 records.

---

# P2 Completeness Audit

Result: **PASS**

The audit closed four gaps:

1. `acquisition_modes` is now explicit for all 28 opportunities.
2. mixed scalar enum values were normalized for deterministic P3 use.
3. `minimum_device` is now explicit for all 28 opportunities.
4. `acquisition_difficulty` and `margin_profile` were added because they are required for the intended opportunity decision model.

`margin_profile` is a structural direct-cost heuristic, not verified pricing or promised profit.

`acquisition_difficulty` is a structural new-entrant heuristic. Future scoring may adjust it when P1 proves existing customers, audience, network or platform access.

---

# Demand Evidence Guardrail

P2 v0 uses current 2026 evidence from:

- Upwork In-Demand Skills / Monthly Hiring Insights
- Fiverr Business Trends Index 2026
- OECD 2026 D4SME Survey

Demand evidence is directional. Do not represent marketplace growth as guaranteed client availability, conversion, pricing or income.

---

# Product Principle

SoloForge should reduce wrong experiments, not merely generate more ideas.

The system is building toward:

> Given this person's actual constraints, evidence and market access, which income experiment has the highest probability of being worth testing first?

---

# P2 Must Remain Closed

Do not retroactively add these to P2:

- personalized ranking
- weighted opportunity scoring
- Flutter UI
- Supabase schema
- billing
- autonomous agents
- paid AI generation
- income guarantees

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking output polish.

Memory Foundation v1 remains shared infrastructure. Chat Prawtwan MVP and Telegram Idea Inbox remain merged capabilities but are not the active Income Engine priority.

---

# Next Development Direction

The next candidate phase is:

`P3 — Eligibility + Opportunity Scoring v0`

P3 should apply, in order:

1. hard eligibility filters
2. confidence-aware capability matching
3. weighted opportunity scoring
4. explanation of why the top path fits
5. explanation of why tempting alternatives were rejected
6. cheap experiment selection

Do not start P3 until the owner explicitly approves progression.

---

# AI Instructions

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Read docs/CURRENT_SPRINT.md.
5. Read the P1 and P2 Income Engine specs.
6. Prefer evidence-backed capability over guessed skill.
7. Run hard eligibility before ranking.
8. Do not reopen completed Asset Forge v1 without explicit owner priority.
9. Do not start P3 until the owner explicitly approves progression.

---

End of Task Board
