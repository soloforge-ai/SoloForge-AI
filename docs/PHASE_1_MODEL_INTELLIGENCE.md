# Phase 1 — Model Intelligence

## Objective

Create a provider-neutral model intelligence layer for SoloForge AI.

The first implementation uses Pollinations as the live discovery source, while keeping the domain model independent from Pollinations so additional providers can be added later.

## Delivered in this phase

- Live model catalog discovery from `https://gen.pollinations.ai/models`.
- Separate official and community model discovery.
- Normalized `AiModel` domain object.
- Modality detection for Text, Image, Video, Audio, Embedding, 3D, and Realtime.
- Capability and pricing metadata preserved without hard-coding provider-specific fields.
- Search by model ID, name, and provider.
- Modality filters.
- Community model visibility.
- Manual catalog refresh.
- Developer Tools entry point.

## Architecture

```text
Developer Tools
      |
      v
Model Intelligence Page
      |
      v
ModelCatalogService
      |
      v
Pollinations Model Catalog
      |
      v
AiModel domain model
```

## Important boundary

`ModelCatalogService` is the provider adapter. The rest of SoloForge should consume `AiModel`, not raw Pollinations JSON.

This allows the next providers to be added without changing the UI or scoring engine.

## Phase 1 does NOT do yet

- API-key storage.
- Image generation.
- Video generation.
- Automated quality benchmarking.
- Paid-cost optimization.
- Provider failover.
- User-facing model selection.

Those belong to later phases after the catalog and data contract are validated.

## Next phase

Phase 1B should add a benchmark runner for the Image Lab:

`same prompt + same reference -> multiple image models -> generated assets -> evaluation -> ModelScore`.

The benchmark must store raw results so model rankings can be recalculated without regenerating assets.
