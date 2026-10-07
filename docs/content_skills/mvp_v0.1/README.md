# SoloForge Content Skill System — MVP v0.1

Status: IMPLEMENTATION STARTED  
Idea: #023 — Content Skill System  
Date: 2026-10-07

## Goal

Turn repeated content-production instructions into reusable, versioned Content Skills so the Content Engine can select a skill, fill variables, produce a storyboard/package, run QA, and send only a compact approval decision to the human.

## MVP Scope

This MVP intentionally implements only one skill:

`SHORT_EDUCATIONAL_V1`

It follows the existing SoloForge experiment-content rules:

- `quality_mode = EXPERIMENT`
- target length: 15–25 seconds
- hard limit: 35 seconds
- default: 3–5 scenes
- formula: `HOOK + ONE IDEA + PROOF/VALUE + CTA`
- reuse existing assets before generating new assets
- human decision: `APPROVE / REVISE / REJECT`

## Runtime Flow

```text
Content Job
  ↓
Skill Router
  ↓
SHORT_EDUCATIONAL_V1
  ↓
Fill Variables
  ↓
Script + Storyboard + Asset Plan
  ↓
Deterministic QA
  ↓
Approval Package
  ↓
APPROVE / REVISE / REJECT
```

## Implementation

Runtime: `backend/asset_forge/backend/content_skill_runtime.py`

Canonical skill data:
`backend/asset_forge/data/content_skills/`

The MVP stops before expensive generation and publishing.
