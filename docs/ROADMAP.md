# SoloForge AI Product Roadmap

> Human-maintained product direction.
>
> Project Scanner must not overwrite this file. Scanner-generated implementation observations belong under `tools/scanner/output/`.

## Active Product Direction

SoloForge Product-to-Post

```text
Product
→ Extract / load product data
→ Evaluate product opportunity
→ Select selling angle
→ Generate creative + caption
→ Review
→ Export ready-to-post package
```

The near-term goal is to prove this workflow with one real product before expanding architecture or adding unrelated verticals.

## NOW — Prove Product-to-Post

1. Obtain a usable live qualification result for a text provider.
2. Keep model qualification separate from workflow execution success.
3. Do not switch the production ContentEngine provider without explicit owner approval.
4. Audit the existing Product Forge path for only the smallest missing end-to-end gaps.
5. Run one real product through `Product → Ready-to-Post`.
6. Verify the result is useful, reviewable, and manually exportable.

Manual steps are acceptable until the commercial workflow is proven.

## COMPLETED / RETAINED

- Product Catalog and discovery foundation
- Feed Processor and MiniBoss ranking
- Product Intelligence and Product Forge foundation
- Content Engine and prompt infrastructure
- Asset Forge v1 — Working Product #1
- Pollinations OAuth/session infrastructure required by Asset Forge
- Character Memory bridge used by Asset Forge runtime
- Asset Forge output-quality processing
- Cleanup Scope Reset #1
- Text Model Qualification Harness
- Live Text Qualification Runner

## NEXT — Only After One Real E2E Pass

Use evidence from the first real Product-to-Post run to decide the next smallest product improvement.

Possible work may include only gaps proven by the E2E result, such as:

- better product input or extraction
- stronger selling-angle selection
- provider integration after qualification approval
- clearer review UX
- practical export packaging
- performance/result tracking needed to close the revenue feedback loop

Do not promote a possible item to active work without owner approval.

## FROZEN / NOT ACTIVE ROADMAP DRIVERS

- Chat Prawtwan expansion
- Idea Flow / Telegram Idea Inbox expansion
- SoloForge Income Engine P2+
- new agent systems
- new memory systems
- billing
- autonomous social posting
- unrelated business verticals
- broad architecture refactors

Existing retained implementations may remain in the repository without being active roadmap priorities.

## Roadmap Authority

Priority order for current project intent:

1. Explicit owner instruction
2. `docs/CURRENT_SPRINT.md` — active human-approved development state
3. `docs/ROADMAP.md` — human-approved product direction
4. `.ai/AI_TASK.md` and `.ai/AI_CONTEXT.md` — synchronized AI working context
5. Project Scanner output — observed implementation only

Generated scanner output must never be used to infer or replace human product intent.

---

Last updated: 2026-09-06 — Scanner authority separation approved.
