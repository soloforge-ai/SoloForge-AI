# SoloForge AI — Phase A V1 Implementation Map

> North Star: SoloForge AI is an AI Creator OS for solo creators. Pollinations is an AI provider inside the product, not the product itself.

## Core V1 workflow

Product → Product Intelligence → Content → AI Creative / Asset → Output

## Current repo mapping

| V1 capability | Current implementation | Phase A action |
|---|---|---|
| Product catalog | `frontend/lib/services/catalog_service.dart` + catalog assets | Keep; use as source of products |
| Product discovery | `frontend/lib/services/discovery/discovery_service.dart` | Keep; use as entry point |
| Product selection | `frontend/lib/pages/home_page.dart` + `frontend/lib/widgets/product_card.dart` | Keep; make Forge workflow the primary path |
| Product intelligence | `frontend/lib/ai/product_intelligence.dart` + Forge analysis UI | Keep; surface inside workflow |
| Content generation | `frontend/lib/ai/content_engine.dart` + `frontend/lib/widgets/forge/content_studio.dart` | Keep; consolidate into V1 workflow |
| Prompt generation | `frontend/lib/services/prompt_engine/*` + `PromptStudio` | Keep; reuse as Asset context builder |
| Asset Forge | `frontend/lib/pages/asset_forge_page.dart` + `backend/asset_forge/` | Keep as provider-backed asset capability; do not replace existing MVP yet |
| Pollinations image generation | Asset Forge backend boundary | Keep behind provider boundary; OAuth is Phase B |
| Export | Existing copy/share/download flows | Keep; improve final-output flow in Phase A |

## Phase A milestones

### A1 — Core workflow shell

Make the product-selection → Forge journey explicit and coherent. A selected product becomes the single context passed through intelligence, content, prompts, and creative creation.

### A2 — Content result as a usable deliverable

Ensure generated hook, caption, CTA, hashtags, and script are presented as one content package with clear copy actions.

### A3 — Product-to-creative handoff

Add a contextual handoff from the selected product and content context into Asset Forge. Do not introduce Pollinations OAuth yet.

### A4 — Final output

Present the resulting creative and content together with copy/download/share actions.

## Explicitly out of scope for Phase A

- Pollinations OAuth/PKCE integration
- Paid Pollen flow
- Pollinations App Directory submission
- External-user growth mechanics
- Billing
- Social auto-publishing
- Large multi-provider management UI
- Replacing the existing Asset Forge backend

## Branch strategy

Phase A work starts from `feature/asset-forge-mvp` and is isolated in:

`feature/phase-a-v1-core-workflow`

Each milestone should be reviewable and merged independently. Do not merge PR #10 into this branch merely because it exists; OAuth belongs to Phase B.
