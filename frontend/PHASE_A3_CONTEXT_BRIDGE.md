# Phase A3 Context Bridge

Goal: connect the product and content workflow to creative prompt generation while keeping provider-specific logic outside the context model.

Flow: Product Intelligence + Content Brief + Platform + Generated Content -> PromptContext -> Image, Video, Voice prompt services -> Asset Forge provider layer.

Included: enriched PromptContext, campaign-aware prompt services, ForgePage to PromptStudio bridge, stale-context invalidation, and a regression test.

Not included: Pollinations OAuth, Paid Pollen, provider selection UI, direct asset generation, social publishing, or UX issues #15 and #16.

Acceptance: generated creative prompts include Goal, Selling Angle, Tone, Platform, Hook, CTA, and hashtags; Flutter analyze, test, and build must pass before merge.
