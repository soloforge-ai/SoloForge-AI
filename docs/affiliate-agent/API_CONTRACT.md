# API Contract V0.1

This document describes the first implementation boundary. It is transport-agnostic so the current SoloForge backend can expose it without forcing a framework rewrite.

## Discover

### GET /affiliate/programs

Query:
- q
- category
- recurring
- min_cookie_days
- free_trial
- limit
- cursor

Response item:
- id
- name
- website
- category
- commission_type
- commission_value
- cookie_days
- recurring
- pricing
- free_trial
- source
- verified_at

Initial source adapter: OpenAffiliate.

## Program detail

### GET /affiliate/programs/{id}

Returns normalized program data, source metadata, and the latest user-specific opportunity score when available.

## Analyze

### POST /affiliate/programs/{id}/analyze

Input:
- niche
- audience

Output:
- audience_fit
- content_potential
- commission_score
- product_value
- competition
- total_score
- rationale
- risks
- content_angles

Scoring weights are fixed by MVP_SPEC.md. AI may provide rationale, but the weighted total is calculated by code.

## My Programs

### POST /affiliate/my-programs
Input:
- program_id
- status

### PATCH /affiliate/my-programs/{id}
Input:
- status
- affiliate_url
- joined_at
- notes

### GET /affiliate/my-programs
Optional status filter.

## Content Factory

### POST /affiliate/content/generate

Input:
- program_id
- platform
- format
- intent
- goal
- audience

Output:
- content_id
- title
- hooks
- script
- shot_list
- voiceover
- visual_prompts
- thumbnail_brief
- cta
- description
- affiliate_disclosure
- claims[]
- tools[]

first_hand_claim and measured_result must default to unverified.

## Content tools

### PUT /affiliate/content/{content_id}/tools

Each tool:
- tool_name
- role
- affiliate_url
- used_in_final_output

The same data feeds the video end card and description.

## Tracking

### POST /affiliate/tracking-links
Input:
- program_id
- content_id
- slug
- target_url

### GET /go/{slug}

Server behavior:
1. Resolve active link.
2. Record click event.
3. Return redirect to target_url.

Never expose service-role credentials to the browser.

## Performance

### GET /affiliate/performance

Returns:
- clicks
- conversions
- revenue
- currency
- conversion_rate
- epc

### POST /affiliate/performance
V0 manual entry:
- program_id
- content_id
- conversions
- revenue
- currency
- period_start
- period_end
