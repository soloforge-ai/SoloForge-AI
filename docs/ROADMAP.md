# SoloForge AI Product Roadmap

> Human-maintained product direction.
>
> Project Scanner must not overwrite this file. Scanner-generated implementation observations belong under `tools/scanner/output/`.

## Source-of-Truth Date

2026-10-01

---

## Active Product Direction

### SoloForge State Reset

The project has enough implemented capability to stop expanding horizontally.

The immediate objective is to convert the current codebase into one clearly defined, verified production baseline.

Active sequence:

```text
Source of Truth
→ PR Cleanup
→ Content Factory E2E Proof
→ Idea #003 Validation Loop
```

No unrelated roadmap expansion should interrupt this sequence.

---

# NOW — State Reset

## Phase 1 — Source of Truth

Synchronize:

- `README.md`
- `docs/CURRENT_SPRINT.md`
- `docs/ROADMAP.md`
- `.ai/AI_CONTEXT.md`

The documentation must distinguish:

- production / verified
- implemented / needs E2E
- retained
- experimental / open PR
- frozen

Success condition:

> A new contributor or AI assistant can identify the current production baseline and next gate without reconstructing project history from old chats or branches.

---

## Phase 2 — PR Cleanup

Review all open pull requests.

Every PR must receive one explicit disposition:

```text
MERGE
CLOSE
ARCHIVE
KEEP
```

Priority review includes current open work related to:

- strategist / campaign planning
- Graphify integration
- subtitle timing
- Affiliate Agent / AI Content Factory
- historical Income Engine branches
- older feature branches that no longer match current direction

Principle:

> Code in an open branch is not part of production until it is intentionally accepted into the current product direction.

Success condition:

> `main` is the unambiguous production baseline.

---

# NEXT — Content Factory E2E Proof

Run one real content idea through:

```text
Idea
→ Analyze / MiniBoss
→ AI Generate
→ Review
→ Approve
→ Asset Generation
→ SoloForge Branding
→ TTS / Final Render when required
→ Ready to Publish
→ Publora
→ Real Published Post
```

## E2E Evidence Requirements

Record at minimum:

- input idea
- content job ID
- MiniBoss score / decision
- generation provider / model where available
- generated hook / script / caption / CTA
- review state
- approval event
- asset state
- storage path or generated media reference
- branding metadata
- audio/render state if required
- Publora post/group ID
- publishing status
- real destination evidence

## E2E Success Condition

The milestone is green only when one real job completes the full intended route.

Green unit tests, APK builds, or backend health checks are necessary supporting evidence but are not substitutes for this proof.

---

# AFTER E2E — Idea #003 Validation Loop

Once the publishing path is proven, SoloForge shifts from a content-production-only model toward a demand-validation model.

Approved business process:

```text
Audience Problem
↓
Content
↓
Lead Magnet
↓
Lead Capture
↓
Observe / Survey Pain
↓
Offer
↓
Pre-sell
↓
Build Only If Validated
↓
Deliver
↓
Measure
```

Core principle:

> **Don't build inventory. Build validated offers.**

Thai operating rule:

> **อย่าผลิตของเพิ่มเพราะเราผลิตได้ — ผลิตเมื่อมีหลักฐานว่าคนต้องการ**

## First Validation Experiment

Use an existing product rather than creating a new inventory item:

**AI Character Consistency Kit**

Target funnel:

```text
AI HackWork Content
↓
Free Character Consistency Mini Checklist
↓
Landing Page
↓
Email Capture
↓
SoloForge Lead DB
↓
3 Useful Emails
↓
AI Character Consistency Kit
↓
Payhip
```

Primary measurements:

- Views
- Landing Page CTR
- Signup %
- Qualified Leads
- Product CTR
- Purchase %
- Revenue per Lead

The purpose is to identify whether failure is caused by distribution, message, offer, pricing, trust, or product-market fit.

---

# COMPLETED / RETAINED FOUNDATIONS

The following foundations should be preserved unless an E2E blocker requires a targeted change:

- Flutter application foundation
- Product Catalog and discovery
- Feed Processor
- MiniBoss ranking
- Product Intelligence / Product Forge foundations
- Content Engine / prompt infrastructure
- Content Job workflow
- idea analysis / content-format recommendation
- AI generation infrastructure
- Asset Forge v1 — Working Product #1
- Pollinations OAuth/session infrastructure
- Character Memory bridge
- output-quality processing
- asset generation
- SoloForge branding
- TTS / audio generation
- subtitle / final render pipeline
- Supabase runtime persistence / storage
- Publora integration
- analytics / performance foundations
- retained Telegram integrations
- Android APK CI
- Render production smoke
- Project Scanner / project intelligence

---

# IMPLEMENTED / NEEDS E2E

Do not promote these to fully production-proven status before the current E2E milestone:

- continuous Idea → Publish orchestration
- live AI provider execution within the exact E2E route
- complete worker progression for a real job
- real Publora publication from that job
- real destination publication confirmation
- closed-loop performance learning
- unattended 24/7 content operation

---

# FROZEN / NOT ACTIVE ROADMAP DRIVERS

- Chat Prawtwan expansion
- Idea Flow / Telegram Idea Inbox expansion
- SoloForge Income Engine P2+
- new agent systems
- new memory systems
- billing
- unrelated product verticals
- broad architecture refactors

Existing retained implementations may remain in the repository without becoming active roadmap priorities.

---

# Roadmap Decision Rule

Before adding a new product capability, ask:

1. Does it block the current E2E proof?
2. Does evidence from the E2E test require it?
3. Does it directly support Idea #003 after E2E?
4. Does it reduce manual work on a proven business loop?

If the answer is no to all four, it should not enter active development.

---

# Roadmap Authority

Priority order for current project intent:

1. Explicit owner instruction
2. `docs/CURRENT_SPRINT.md`
3. `docs/ROADMAP.md`
4. `.ai/AI_CONTEXT.md`
5. `.ai/AI_TASK.md`
6. Project Scanner output

Generated scanner output must never replace human-approved product direction.

---

Last updated: 2026-10-01 — State Reset sequence approved: Source of Truth → PR Cleanup → Content Factory E2E Proof → Idea #003 Validation Loop.
