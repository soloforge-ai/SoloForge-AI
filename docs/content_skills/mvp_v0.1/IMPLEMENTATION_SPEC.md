# Implementation Spec — Content Skill System MVP v0.1

## 1. Architectural position

The Content Skill is **SoloForge-owned logic**. Model providers, image/video providers, voice providers, and execution agents are adapters.

```text
Content Job
→ Skill Router
→ Content Skill
→ Structured Production Plan
→ Provider Adapters
→ QA
→ Approval Queue
→ Execution
```

Core skill data must remain provider-agnostic.

## 2. First skill

`SHORT_EDUCATIONAL_V1`

Why first:
- matches the existing EXPERIMENT content mode
- naturally fits 15–25 second short-form content
- uses 3–5 scenes
- can reuse existing assets heavily
- is easy to evaluate deterministically
- is commercially useful for education, proof, and problem-aware content

## 3. State model

```text
DRAFT
→ PLANNED
→ STORYBOARD_READY
→ READY_FOR_APPROVAL
→ APPROVED
→ ASSET_GENERATION
→ ASSEMBLY
→ QA
→ READY_TO_PUBLISH
```

For v0.1, stop at `READY_FOR_APPROVAL`.

No publishing logic is introduced by this MVP.

## 4. Router contract

The router receives:
- content goal
- topic
- audience
- platform
- risk/production mode

For MVP:
- if goal is educational/problem/proof short-form and duration <= 35 sec → `SHORT_EDUCATIONAL_V1`
- otherwise → `UNSUPPORTED` and require manual selection

Do not invent extra skills automatically.

## 5. Required invariants

1. One content job = one primary idea.
2. One content job = one CTA.
3. 3–5 scenes in EXPERIMENT mode.
4. Hard duration ceiling = 35 seconds.
5. Existing assets are preferred over generation.
6. Expensive generation cannot begin before storyboard approval.
7. Character content must use Character Lock when available.
8. QA must be machine-readable.
9. Human review must be a compact `APPROVE / REVISE / REJECT` decision.
10. Provider-specific prompt wording must not become the source of truth.

## 6. Minimal integration surface

Recommended application interfaces:

```text
ContentSkillRegistry.get(skill_id)
ContentSkillRouter.select(job)
ContentSkillPlanner.plan(job, skill)
ContentSkillQA.validate(plan, skill)
ApprovalPackageBuilder.build(plan, qa)
```

Do not build a large framework yet.

## 7. Success criteria for MVP

The experiment passes when all are true:

- the same skill can generate at least 5 distinct content jobs without rewriting the workflow prompt
- average human instruction is reduced to topic/audience/goal/CTA + optional facts/assets
- output is always structured
- QA catches scene/duration/CTA violations
- approval package can be understood without rereading the full generation conversation
- no expensive asset generation happens before approval

## 8. Metrics

Track manually first:

```text
human_prompt_minutes
human_review_minutes
revision_count
new_assets_generated
assets_reused
qa_failures
time_to_ready_for_approval
```

Do not build analytics infrastructure until the first 5–10 jobs have been run.

## 9. Next gate

After 5–10 successful jobs:

```text
PASS
→ add second skill based on repeated real workflow

FAIL
→ fix the skill contract/rules before adding more skills
```

Potential second skills are deliberately not approved in v0.1.
