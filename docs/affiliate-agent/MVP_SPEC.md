# MVP Specification V0

## Primary user job

For my niche and audience, find affiliate programs worth testing and turn one selected program into publishable content with measurable outbound clicks.

## Primary flow

1. Select niche/audience.
2. Search affiliate programs.
3. Filter and inspect program details.
4. Calculate deterministic opportunity score.
5. Save program to My Programs.
6. Track application status and personal affiliate URL.
7. Generate content package.
8. Human-verify claims requiring real-world use.
9. Publish externally.
10. Route clicks through a tracking URL.
11. Record clicks, conversions, and revenue.
12. Use real performance to influence future recommendations.

## V0 pages

### Discover
- Search by keyword/category/niche.
- Filters: recurring, cookie threshold, free trial, category.
- Result cards show program basics and opportunity score.

### Program Detail
- Website/category/pricing/free-trial.
- Commission type/value.
- Cookie window.
- Application URL.
- Source and last verified time.
- Audience-fit explanation.
- Content opportunities.
- Risks/restrictions.
- Save and Apply actions.

### My Programs
Statuses:
- discovered
- interested
- applied
- approved
- rejected
- active
- paused

Stores personal affiliate URL and notes.

### Content Factory
Inputs:
- program
- audience
- platform
- format
- goal

Outputs:
- title options
- hooks
- script
- shot list
- voiceover copy
- visual prompts
- CTA
- description
- affiliate disclosure
- tool list
- end-card data

### Tracking
- Generate first-party redirect slug.
- Example: /go/{slug}
- Record click event before redirecting to personal affiliate URL.

### Performance
Show:
- clicks
- conversions
- revenue
- conversion rate
- EPC (revenue / clicks)

Conversions and revenue may be entered manually in V0.

## Opportunity score

Total =
- Audience Fit 30%
- Content Potential 25%
- Commission 20%
- Product Value 15%
- Competition 10%

The score is a prioritization heuristic, not ground truth. Once real performance exists, real revenue data outranks the heuristic.

## Acceptance criteria

V0 is not complete until:
- affiliate search works
- filters work
- program details open
- score is computed deterministically
- program can be saved
- status persists
- personal affiliate URL persists
- content package can be generated
- unverified claims are visibly flagged
- tracking URL redirects correctly
- click is recorded
- refresh does not lose saved data
- performance page shows clicks
- manual conversions/revenue can be recorded
- end-card/tool metadata can be produced for each content item

## Explicitly out of scope

- social auto-posting
- automatic video rendering
- subscription billing
- teams
- browser extension
- native mobile app
- network-wide conversion APIs
- advanced attribution
- SEO site generator
- complex dashboarding
