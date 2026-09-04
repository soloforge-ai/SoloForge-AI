# SoloForge AI Task Board

Version: v1.8.0

---

# Current Work

Title

SoloForge Income Engine — P3 Eligibility + Opportunity Scoring v0

Status

Validated — PASS

Primary Specs

- `docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`
- `docs/INCOME_ENGINE_P2_OPPORTUNITY_LIBRARY.md`
- `docs/INCOME_ENGINE_P3_ELIGIBILITY_SCORING.md`

---

# Completed Gates

- P1 — Income Diagnostic v0: **PASS**
- P2 — Opportunity Library v0: **PASS**
- P3 — Eligibility + Opportunity Scoring v0: **PASS (manual decision-model dry run)**

---

# P3 Goal Achieved

SoloForge now has a controlled decision model that can combine evidence-backed P1 user profiles with deterministic P2 opportunity metadata without relying on free-form LLM ranking.

The required decision order is:

1. hard eligibility
2. capability uncertainty / verification
3. weighted scoring
4. recommendation confidence
5. explanation of fit and rejection
6. cheap validation experiment

---

# P3 Fit Score

Weights:

- Capability Fit: 25
- Revenue Timing Fit: 20
- Acquisition Reachability: 15
- Execution Fit: 15
- Market Evidence: 10
- Margin Profile: 5
- Recurring Revenue: 5
- Scalability: 3
- AI Leverage: 2

Total: 100

The score is a heuristic fit score. Never present it as probability of success, expected revenue, guaranteed conversion, or financial return.

---

# Decision States

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

The model is required to return no-match/discovery states when evidence is insufficient instead of filling the gap with generic online-income advice.

---

# P3 Validation

The same 10 personas from P1 were manually dry-run through the P3 decision contract.

Validated behaviors include:

- materially different profiles lead to materially different opportunity families
- hard device/budget/interaction/public/timing constraints execute before ranking
- distribution-dependent paths are demoted for urgent users without distribution assets
- unknown skill can return `DISCOVERY_REQUIRED`
- capital without execution evidence can return `NO_CONFIDENT_MATCH`
- acquisition reachability improves when P1 proves customers, audience, network or channel access
- recommendation explanations must cite P1 evidence + P2 metadata
- the next action is the P2 cheap validation experiment, not a large speculative business plan

Result: **PASS**

This PASS validates the decision-model specification only. It is not a production implementation and not evidence of real-world revenue outcomes.

---

# Guardrails

Do not:

- generate new opportunities dynamically during scoring
- use LLM popularity as fit
- bypass hard eligibility
- convert tool exposure into proven capability
- force a recommendation when confidence is low
- call Fit Score a success probability
- promise income
- add Flutter UI during P3
- add Supabase schema during P3
- add billing
- add autonomous execution

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking output polish.

Memory Foundation v1 remains shared infrastructure. Chat Prawtwan MVP and Telegram Idea Inbox remain merged capabilities but are not the active Income Engine priority.

---

# Next Development Direction

The next candidate phase is:

`P4 — Deterministic Recommendation Engine Prototype`

P4 should:

- encode P1/P2/P3 as machine-readable contracts
- implement hard eligibility + scoring without free-form LLM ranking
- add automated fixtures for the 10 personas
- return structured recommend/two-way-test/discovery/no-match output
- remain local/testable before Flutter UI or production persistence

Do not start P4 until the owner explicitly approves progression.

---

# AI Instructions

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Read docs/CURRENT_SPRINT.md.
5. Read P1/P2/P3 Income Engine specs.
6. Prefer evidence-backed capability over guessed skill.
7. Run hard eligibility before ranking.
8. Preserve valid no-match states.
9. Do not reopen completed Asset Forge v1 without explicit owner priority.
10. Do not start P4 until the owner explicitly approves progression.

---

End of Task Board
