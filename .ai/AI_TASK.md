# SoloForge AI Task Board

Version: v1.6.0

---

# Current Work

Title

SoloForge Income Engine — P2 Opportunity Library v0

Status

In Validation

Primary Specs

- `docs/INCOME_ENGINE_P1_DIAGNOSTIC.md`
- `docs/INCOME_ENGINE_P2_OPPORTUNITY_LIBRARY.md`

---

# Completed Gate

P1 — Income Diagnostic v0: **PASS**

The validated diagnostic can distinguish materially different users, preserve unknown skills as unknown, retain hard constraints, and attach evidence/confidence to inferred capabilities without producing premature income recommendations.

---

# P2 Goal

Create a controlled opportunity library that later eligibility/ranking logic can evaluate against P1 profiles.

P2 exists to stop the system from inventing generic income paths from LLM popularity.

---

# P2 Scope

- 28 distinct opportunities across service, productized service, operations, creative, technical implementation, digital product, content and platform work
- startup cost
- time to first revenue
- capability requirements
- device constraints
- customer interaction
- public presence
- acquisition mode
- recurring revenue potential
- scalability
- AI leverage
- demand evidence quality
- hard disqualifiers
- cheap validation experiments

---

# Current Demand Evidence

P2 v0 uses current 2026 evidence from:

- Upwork In-Demand Skills / Monthly Hiring Insights
- Fiverr Business Trends Index 2026
- OECD 2026 D4SME Survey

Demand evidence is directional. Do not represent marketplace growth as guaranteed client availability, conversion, pricing or income.

---

# Guardrails

P2 must:

- use controlled opportunity metadata rather than free-form LLM guesses
- distinguish fast-income service paths from long-horizon distribution-dependent paths
- make hard constraints explicit
- preserve skill uncertainty from P1
- include opportunities that can be excluded before ranking
- keep affiliate/content/media paths available but never assume they are beginner defaults

P2 must not:

- rank a specific person
- implement weighted scoring
- add Flutter UI
- add Supabase schema
- add billing
- add autonomous agents
- add paid AI generation
- promise income

---

# P2 Acceptance Gate

P2 passes only if:

1. at least 20 meaningfully distinct opportunities exist
2. multiple economic models are represented
3. metadata supports later eligibility filtering
4. urgent and long-horizon revenue paths are distinguishable
5. budget/device/capability/customer/public constraints are explicit
6. distribution-dependent paths are not labeled fast/predictable
7. each opportunity includes a cheap validation experiment
8. demand claims include evidence quality
9. no personalized ranking occurs

---

# Completed Product Scope Retained

Asset Forge v1 remains closed as Working Product #1 with the contract 4 poses / 1 AI generation and local review/fix/export. GitHub Issue #48 remains non-blocking output polish.

Memory Foundation v1 remains shared infrastructure. Chat Prawtwan MVP and Telegram Idea Inbox remain merged capabilities but are not the active Income Engine priority.

---

# Next Development Direction

Validate P2 library completeness and constraint coverage.

Only after P2 passes and the owner explicitly approves progression may P3 begin:

`P3 — Eligibility + Opportunity Scoring v0`

---

# AI Instructions

1. Read PROTOCOL.md.
2. Read AI_CONTEXT.md.
3. Follow AI_RULES.md.
4. Read docs/CURRENT_SPRINT.md.
5. Read the P1 and P2 Income Engine specs.
6. Prefer evidence-backed capability over guessed skill.
7. Do not rank users during P2.
8. Do not reopen completed Asset Forge v1 without explicit owner priority.
9. Do not start P3 until P2 passes and the owner explicitly approves progression.

---

End of Task Board
