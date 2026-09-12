# Phase 1B — Image Lab Benchmark

## Objective

Build a reproducible benchmark for comparing image-generation models using the same prompt, reference assets, dimensions, and evaluation criteria.

The benchmark is provider-neutral. Pollinations is the first execution provider because Phase 1 already exposes its live model catalog.

## Core flow

```text
Benchmark Case
  -> Prompt + Reference + Parameters
  -> Selected Image Models
  -> Generation Runner
  -> Raw Generated Assets
  -> Evaluation
  -> ModelScore
  -> Ranking by Use Case
```

## Benchmark principles

1. Same input for every model in a comparison.
2. Store raw outputs and metadata before calculating scores.
3. Never overwrite historical benchmark results.
4. Separate objective metadata from subjective quality scores.
5. Rankings must be reproducible from stored results.
6. Keep provider/model identifiers so results remain auditable.

## Initial benchmark dimensions

- Prompt adherence
- Reference adherence
- Character consistency
- Composition
- Visual quality
- Commercial readiness
- Text rendering when applicable
- Artifact/error rate
- Generation latency
- Estimated generation cost

## ModelScore contract

Each result should eventually contain:

```text
benchmarkId
runId
provider
modelId
promptId
referenceIds[]
parameters
assetUrl
createdAt
durationMs
estimatedCost
qualityScores{}
overallScore
status
error
```

## Initial Image Lab model shortlist

The first benchmark should select a small representative set from the live catalog rather than testing every available model. The shortlist should cover different model families and use cases, then expand after the scoring pipeline is validated.

Recommended first candidates when available in the live catalog:

- flux
- nanobanana-2
- nanobanana-pro
- seedream5
- seedream5-pro
- gpt-image-2
- ideogram-v4-quality
- grok-imagine-image-2.0

The runner must verify that each model is currently available and image-capable before execution; do not hard-code availability as a permanent fact.

## Benchmark cases

Start with 3 reusable cases:

### Case A — Character consistency

A fixed CEO/MiniBoss reference image + controlled scene prompt.

Purpose: measure identity preservation and reference adherence.

### Case B — Commercial product creative

A fixed product reference + advertising prompt.

Purpose: measure product fidelity, composition, visual hierarchy, and commercial readiness.

### Case C — Text-in-image

A controlled promotional composition containing a short headline.

Purpose: measure typography/text rendering and layout adherence.

## Phase 1B implementation boundary

Phase 1B should initially provide the benchmark data contract and runner architecture. API-key storage and production billing logic remain outside the benchmark domain.

The benchmark runner should use a provider adapter so the UI and scoring layer never depend directly on Pollinations request/response formats.

## Persistence

Raw benchmark results are the source of truth. Aggregated rankings are derived data and can be regenerated.

Suggested future structure:

```text
assets/data/benchmarks/
  cases.json
  runs.json
  model_scores.json
```

Generated media should be referenced by durable media IDs/URLs rather than embedded in score records.

## Exit criteria

Phase 1B is complete when SoloForge can:

- Load benchmark cases.
- Select currently available image models.
- Execute the same case against multiple models through a provider adapter.
- Persist raw result metadata.
- Record evaluation scores independently from generation.
- Produce a reproducible ranking by benchmark case.

## Explicit non-goals

- Automatic claims that one model is universally best.
- Training a proprietary image model.
- Production user billing.
- Exposing API keys in Flutter client code.
- Benchmarking every model before the evaluation contract is proven.
