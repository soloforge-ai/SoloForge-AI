# Phase A2 — Content Workflow

## Goal

Turn a selected product into an intentional content brief and pass that brief into the existing Content Engine.

## V1 flow

Product → Product Intelligence → Content Brief → Content Generation → Output

## Brief controls

- Goal: Sell / Educate / Engage
- Selling angle: Best Value / Problem → Solution / Key Benefit / Lifestyle
- Tone: Engaging / Friendly / Premium / Direct

## Scope

- Keep the existing Content Engine and provider boundary.
- Make the prompt aware of the selected brief.
- Keep Pollinations OAuth/PKCE and Asset Forge provider integration out of A2.
- Do not add social publishing or account/billing features.

## Acceptance criteria

1. A product can be opened in AI Forge.
2. The user can select Goal, Angle, and Tone.
3. Generate Content uses those selections in the content prompt.
4. Existing content outputs (Hook, Caption, Hashtags, CTA) remain available.
5. Flutter analyze, tests, and web build succeed before merge.
