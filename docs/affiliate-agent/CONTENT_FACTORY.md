# Content Factory

## Positioning

Ai HackWork: "ใช้ AI เยี่ยงทาส" — AI does the repetitive production work, while claims that depend on actual use are verified by a human.

## Content generation pipeline

Program data
→ Content opportunity
→ Research
→ Hook
→ Script
→ Shot list
→ Voice/visual/video/edit plan
→ Description + CTA
→ Affiliate disclosure
→ Human verification
→ Publish
→ Track
→ Learn

## Required content outputs

For each content item store/generate:
- title
- hook variants
- script
- platform
- format
- intent
- CTA
- shot list
- voiceover
- visual prompt
- thumbnail copy/brief
- description
- hashtags where useful
- affiliate disclosure
- required evidence
- tool list
- end-card payload

## Verification rule

Claims are classified as:
- sourced_fact
- product_claim
- first_hand_claim
- measured_result

first_hand_claim and measured_result must remain UNVERIFIED until real evidence is entered.

Example:
- Claim: "This workflow saves 70% of the time."
- Evidence required: manual duration and AI-assisted duration.
- Publish gate: cannot present as verified until evidence is recorded.

## Standard video end card

Duration target: 3–5 seconds.

Structure:
- "เบื้องหลังคลิปนี้"
- Script: {tool}
- Voice: {tool}
- Visual: {tool}
- Video: {tool}
- Edit: {tool}
- Automation: {tool}
- Closing line: "ทดลองจริง ใช้จริง แล้วค่อยเล่า"

Only tools marked used_in_final_output=true appear.

## Business rule

The tool list should also feed:
- video description
- affiliate disclosure
- affiliate links when available
- internal analytics by tool and content item


## Current implementation

The first live Content Factory path is available from Affiliate Agent → Create Content.

It uses the user's connected Pollinations session for text generation and returns a structured package:

- title and hook options
- script
- shot list
- voiceover
- visual prompts
- thumbnail brief
- CTA
- description
- affiliate disclosure
- claims requiring verification
- tool metadata
- end-card payload

The backend forcibly keeps generated claims unverified. In particular, first-hand and measured-result claims require real evidence before they may be treated as verified.

At this stage the end card lists only tools actually used by the current generation step. Visual/video/edit tools are added only when they are genuinely used in later production stages.
