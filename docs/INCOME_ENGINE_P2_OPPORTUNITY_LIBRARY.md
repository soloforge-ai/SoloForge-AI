# SoloForge Income Engine — P2 Opportunity Library v0

Status: Definition / Validation

Date: 2026-09-04

## Purpose

P2 defines a controlled library of income opportunities that later phases can match against the evidence-backed user profiles produced by P1.

The library exists to prevent a language model from inventing popular online-income ideas on demand and sending many different users toward the same generic paths.

P2 does **not** rank opportunities for a person yet. Personalized ranking belongs to P3.

## Product Principle

SoloForge should reduce wrong experiments, not merely produce more ideas.

Every opportunity must therefore describe:

- what the user actually sells
- who buys it
- realistic startup requirements
- likely time-to-first-revenue band
- capabilities required
- customer-acquisition mode
- public-presence requirements
- recurring-revenue potential
- scalability
- AI leverage
- hard disqualifiers
- the cheapest sensible validation experiment
- current demand-evidence quality

## Evidence Policy

Market demand must not be guessed from LLM familiarity.

P2 uses three demand-evidence levels:

- `A — current explicit evidence`: recent marketplace or business-demand data directly supports the service category.
- `B — durable workflow demand`: common recurring business workflow with credible current demand, but without a precise recent category-growth figure in the evidence set.
- `C — distribution-dependent/speculative`: monetization depends heavily on audience, algorithms, marketplace discovery, or delayed compounding and should not be treated as a fast-income default.

Demand evidence is directional. It is **not** a guarantee of client availability, pricing, conversion, or income.

## Current Market Evidence Used for v0

The following sources inform the initial demand tags:

1. Upwork, `In-Demand Skills 2026`
   - AI video generation/editing +329% YoY
   - AI integration +178%
   - AI data annotation/labeling +154%
   - AI image generation/editing +95%
   - AI chatbot development +71%
   - strong continued hiring in data analytics, graphic design, virtual assistance, web work, lead generation and human-led operational work
   - https://www.upwork.com/research/in-demand-skills-2026

2. Upwork, `Monthly Hiring Insights — July 2026`
   - AI automation was the most-searched AI term
   - growing searches for AI video creator, AI integration and production-oriented AI roles
   - creative demand in video animation and social-media design accelerated
   - https://www.upwork.com/research/upwork-monthly-hiring-insights-july-2026

3. Fiverr, `Business Trends Index 2026: AI Automation Edition`
   - AI UGC video ads +265%
   - short-form video editing +27%
   - Excel data cleaning +210%
   - PDF-to-Excel +153%
   - n8n AI automation +125%
   - Canva designers +403%
   - Instagram content +149%
   - Reels editing +57%
   - YouTube thumbnails +52%
   - translation +55%
   - document formatting +71%
   - https://www.fiverr.com/resources/guides/reports/business-trends-index-june-2026

4. OECD, `Empowering SMEs in the age of AI — 2026 D4SME Survey`
   - SMEs are adopting off-the-shelf AI rapidly
   - strategic integration remains uneven
   - time constraints, maintenance cost and skill gaps remain important barriers
   - this supports implementation/operations services that convert AI tools into usable business workflows
   - https://www.oecd.org/en/publications/empowering-smes-in-the-age-of-ai_bf5a9816-en.html

## Normalized Metadata Contract

Each opportunity uses these fields:

```text
id
name
model_type
buyer
core_deliverable
startup_cost_band
time_to_first_revenue
required_capabilities
minimum_device
customer_interaction
public_presence
acquisition_modes
recurring_revenue_potential
scalability
ai_leverage
market_demand_signal
evidence_level
hard_disqualifiers
cheap_validation_experiment
notes
```

### Startup cost bands

- `zero`: can begin with existing free tools/device
- `very_low`: usually <= THB 500
- `low`: usually <= THB 2,000
- `moderate`: usually <= THB 10,000
- `capital_required`: meaningfully above that or inventory/ad-spend dependent

These bands are implementation heuristics, not promised costs.

### Time-to-first-revenue bands

- `fast`: plausible to validate/sell within 7 days when skill and outreach are already present
- `short`: 8–30 days
- `medium`: 1–3 months
- `long`: more than 3 months or strongly distribution-dependent

These describe opportunity structure, not guaranteed outcomes.

### Customer interaction

- `low`
- `medium`
- `high`

### Public presence

- `none`
- `voice_optional`
- `camera_optional`
- `camera_preferred`

### Recurring-revenue potential

- `low`
- `medium`
- `high`

### Scalability

- `low`: mostly tied to seller hours
- `medium`: can standardize/delegate/productize
- `high`: product/audience/system can serve many buyers

### AI leverage

- `assistive`: AI improves speed/quality
- `strong`: AI materially changes economics or production capacity
- `core`: the offer itself depends on AI implementation

## Opportunity Library v0

| ID | Opportunity | Model | Startup | First Revenue | Customer Interaction | Public Presence | Recurring | Scale | AI Leverage | Demand / Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| O01 | Spreadsheet Data Cleanup | Service | zero | fast | medium | none | medium | medium | strong | A |
| O02 | PDF / Document to Spreadsheet Conversion | Service | zero | fast | low-medium | none | low-medium | medium | strong | A |
| O03 | Dashboard & Business Reporting | Service | very_low | short | medium | none | high | medium | strong | B |
| O04 | Virtual Admin / Operations Assistant | Service | zero | fast-short | high | none | high | low-medium | assistive | A/B |
| O05 | Customer Support / Inbox Management | Service | zero | fast-short | high | none | high | low-medium | assistive | B |
| O06 | Lead Research / Prospect List Building | Service | zero | fast-short | low-medium | none | medium | medium | strong | B |
| O07 | Outreach / Appointment Setting Support | Service | zero | fast-short | high | voice_optional | high | medium | assistive | B |
| O08 | Presentation & Document Formatting | Service | zero | fast-short | medium | none | medium | medium | strong | A |
| O09 | Translation / Localization | Service | zero | fast-short | medium | none | medium | medium | assistive | A |
| O10 | Short-form Video Editing | Service | very_low | short | medium | none | high | medium | strong | A |
| O11 | AI UGC / Ad Creative Production | Service | low | short | medium | camera_optional | high | medium | core | A |
| O12 | Social Media Content Pack | Productized Service | very_low | short | medium | none | high | medium-high | strong | A/B |
| O13 | Canva Social Design | Service | very_low | short | medium | none | high | medium | strong | A |
| O14 | YouTube Thumbnail Design | Service | very_low | short | medium | none | high | medium | strong | A |
| O15 | E-commerce Listing Optimization | Service | zero-very_low | short | medium | none | high | medium | strong | B |
| O16 | Marketplace Store Operations Support | Service | zero | short | high | none | high | low-medium | assistive | B |
| O17 | AI Product Visual / Image Editing | Service | very_low | short | medium | none | medium-high | medium | core | A |
| O18 | Content Repurposing | Productized Service | zero-very_low | short | medium | none | high | medium-high | strong | A/B |
| O19 | AI Workflow Automation | Service | low | medium | high | none | high | medium-high | core | A |
| O20 | Chatbot / FAQ Bot Setup | Service | low | medium | high | none | high | medium-high | core | A |
| O21 | Landing Page / No-code Site Setup | Service | low | short-medium | high | none | medium | medium | strong | B |
| O22 | AI App / Prototype Implementation | Service | low-moderate | medium | high | none | medium-high | medium-high | core | A |
| O23 | Data Annotation / Labeling | Service / Platform Work | zero | short | low-medium | none | low-medium | low | assistive | A |
| O24 | Tutoring / Explainer Service | Service | zero | fast-short | high | voice_optional | high | low-medium | assistive | B |
| O25 | Digital Templates | Product | very_low | medium-long | low | none | medium | high | strong | C |
| O26 | Niche Digital Asset Packs | Product | very_low | medium-long | low | none | medium | high | strong | C |
| O27 | Affiliate Content | Content / Commission | very_low-low | medium-long | low | camera_optional | medium | high | strong | C |
| O28 | Faceless YouTube Channel | Content / Media Asset | low-moderate | long | low | none | medium-high | high | strong | C |

## Opportunity Details

### O01 — Spreadsheet Data Cleanup

Buyer:
- SMEs, ecommerce sellers, offices, agencies, teams with messy operational spreadsheets

Core deliverable:
- cleaned, deduplicated, standardized spreadsheet with validation/reconciliation notes

Required capabilities:
- spreadsheet fluency
- attention to detail
- basic data reasoning

Minimum device:
- computer strongly preferred

Acquisition modes:
- direct SME outreach
- freelance marketplace
- existing professional network

Hard disqualifiers:
- phone-only user for non-trivial files
- no practical spreadsheet evidence unless skill verification is completed first

Cheap validation experiment:
- create one before/after sample using synthetic messy data and offer a fixed-scope cleanup to 10–20 prospects

Notes:
- Fiverr reported +210% search growth for Excel data cleaning.

### O02 — PDF / Document to Spreadsheet Conversion

Buyer:
- offices, logistics teams, sellers, finance/admin teams needing structured extraction

Core deliverable:
- accurate structured Excel/Sheets output from PDFs/forms/documents

Required capabilities:
- careful checking
- spreadsheet basics
- document handling

Minimum device:
- computer preferred

Hard disqualifiers:
- user unwilling to perform manual QA

Cheap validation experiment:
- build a 3-page sample conversion showing raw document versus validated spreadsheet output

Notes:
- Fiverr reported +153% demand growth for PDF-to-Excel.

### O03 — Dashboard & Business Reporting

Buyer:
- SMEs and managers with recurring sales/operations data

Core deliverable:
- recurring dashboard/report with defined KPIs and data-refresh process

Required capabilities:
- spreadsheet/data reasoning
- dashboard tool familiarity
- stakeholder clarification

Minimum device:
- computer

Hard disqualifiers:
- no evidence of data/reporting capability

Cheap validation experiment:
- create one niche-specific demo dashboard from public/synthetic data and ask 10 target businesses whether the KPIs match their weekly decisions

### O04 — Virtual Admin / Operations Assistant

Buyer:
- founders, small teams, online sellers, professionals

Core deliverable:
- scheduling, follow-up, document handling, order/admin coordination, routine operations

Required capabilities:
- reliability
- organization
- written communication

Minimum device:
- phone can work for simple scope; computer preferred for broader scope

Hard disqualifiers:
- extremely low customer interaction tolerance
- highly inconsistent availability for response-sensitive work

Cheap validation experiment:
- offer a one-week fixed-scope admin cleanup/follow-up package to a small business or professional contact

### O05 — Customer Support / Inbox Management

Buyer:
- ecommerce sellers, service businesses, creators, SMEs

Core deliverable:
- response handling, FAQ support, order follow-up, escalation notes

Required capabilities:
- communication
- patience
- process discipline

Hard disqualifiers:
- low interaction tolerance
- inability to maintain agreed response windows

Cheap validation experiment:
- build a sample FAQ + response workflow for one business category and pitch a limited inbox-coverage trial

### O06 — Lead Research / Prospect List Building

Buyer:
- B2B sellers, agencies, consultants, recruiters

Core deliverable:
- researched target list with defined qualification fields

Required capabilities:
- research
- structured data handling
- judgment against criteria

Hard disqualifiers:
- weak research discipline
- no computer for larger research tasks

Cheap validation experiment:
- produce 20 sample prospects for one narrowly defined buyer profile and ask a seller to rate relevance

### O07 — Outreach / Appointment Setting Support

Buyer:
- local businesses, agencies, consultants, B2B service providers

Core deliverable:
- prospect outreach, follow-up and qualified appointment booking

Required capabilities:
- customer interaction tolerance
- sales resilience
- clear written/voice communication depending channel

Hard disqualifiers:
- low sales/customer-contact tolerance

Cheap validation experiment:
- run a 20-prospect manual outreach test for one clear offer and record reply rate, interest and objections

### O08 — Presentation & Document Formatting

Buyer:
- students, professionals, SMEs, consultants, authors

Core deliverable:
- polished slides/documents, formatting, layout cleanup, consistency

Required capabilities:
- visual organization
- document tools
- careful editing

Hard disqualifiers:
- no evidence of document/presentation ability for higher-complexity work

Cheap validation experiment:
- publish three before/after examples from synthetic documents/slides

Notes:
- Fiverr reported +71% growth in formatting-related demand.

### O09 — Translation / Localization

Buyer:
- creators, ecommerce sellers, websites, SMEs, publishers

Core deliverable:
- translated/localized copy with human review and contextual adaptation

Required capabilities:
- strong language proficiency
- nuance and QA

Hard disqualifiers:
- weak target-language proficiency
- reliance on raw machine translation without review

Cheap validation experiment:
- create a side-by-side localization sample for one product page or short video script

Notes:
- Fiverr reported +55% growth in translation demand.

### O10 — Short-form Video Editing

Buyer:
- creators, ecommerce sellers, SMEs, agencies

Core deliverable:
- vertical short video ready to post, including pacing/cuts/captions where scoped

Required capabilities:
- editing workflow
- storytelling/pacing
- visual QA

Minimum device:
- capable phone may work; computer improves throughput

Hard disqualifiers:
- device incapable of required editing workload

Cheap validation experiment:
- edit three short samples from licensed/self-created footage and pitch a fixed 5-video starter pack

Notes:
- Fiverr reported +27% growth for short-form video editing; Upwork reports strong AI-video/editing growth.

### O11 — AI UGC / Ad Creative Production

Buyer:
- ecommerce brands, agencies, advertisers

Core deliverable:
- creator-style ad concepts/videos produced with AI and human QA

Required capabilities:
- ad concept judgment
- script/pacing
- AI video workflow

Public presence:
- camera can be optional if synthetic/asset-based production is allowed

Hard disqualifiers:
- no ability to review claims/brand safety
- insufficient device/tool access for production

Cheap validation experiment:
- create two spec ads for a fictional or owned product and ask 5–10 marketers/sellers which hook they would test

Notes:
- Fiverr reported +265% growth for AI UGC video ads; Upwork identifies AI UGC as a fast-growing AI search.

### O12 — Social Media Content Pack

Buyer:
- local SMEs, solo businesses, ecommerce sellers

Core deliverable:
- recurring bundle of posts, short scripts, visual assets and captions for defined channels

Required capabilities:
- content planning
- basic visual/copy judgment
- client communication

Hard disqualifiers:
- no ability to maintain consistent delivery cadence

Cheap validation experiment:
- make a 7-day sample pack for one niche and offer it to 10 businesses in that niche

### O13 — Canva Social Design

Buyer:
- SMEs, creators, ecommerce sellers, event/community operators

Core deliverable:
- repeatable branded social graphics/templates

Required capabilities:
- visual design
- Canva fluency

Hard disqualifiers:
- tool exposure without evidence should not qualify user for advanced design work

Cheap validation experiment:
- create one 6-post visual set for a sample brand and seek feedback/orders from a defined business niche

Notes:
- Fiverr reported +403% growth for Canva designer searches.

### O14 — YouTube Thumbnail Design

Buyer:
- YouTubers, agencies, media teams

Core deliverable:
- clickable, brand-consistent thumbnails

Required capabilities:
- visual composition
- image editing
- packaging judgment

Hard disqualifiers:
- no portfolio/evidence of visual capability

Cheap validation experiment:
- redesign three existing public thumbnails as non-commercial portfolio exercises and contact 10 channels with one tailored sample

Notes:
- Fiverr reported +52% growth for YouTube thumbnail demand.

### O15 — E-commerce Listing Optimization

Buyer:
- marketplace sellers and small ecommerce brands

Core deliverable:
- improved titles, descriptions, image order, attributes, keyword/benefit structure and listing QA

Required capabilities:
- copy/research
- product understanding
- platform familiarity

Hard disqualifiers:
- no relevant platform access or ability to evaluate product claims accurately

Cheap validation experiment:
- rewrite one weak listing into a before/after sample and ask sellers to evaluate clarity and conversion relevance

### O16 — Marketplace Store Operations Support

Buyer:
- small ecommerce sellers

Core deliverable:
- listing updates, order/admin follow-up, campaign setup support, catalog maintenance

Required capabilities:
- operational discipline
- platform familiarity
- customer communication

Hard disqualifiers:
- cannot maintain response/service windows

Cheap validation experiment:
- offer one fixed catalog cleanup or listing-maintenance session instead of a vague VA package

### O17 — AI Product Visual / Image Editing

Buyer:
- ecommerce sellers, local brands, creators

Core deliverable:
- cleaned/enhanced product visuals, background variations, ad-ready compositions under clear authenticity rules

Required capabilities:
- image judgment
- AI/image editing tools
- QA

Hard disqualifiers:
- inability to avoid misleading product representation

Cheap validation experiment:
- create 3 before/after examples using owned or permitted product images and pitch a 5-image starter pack

Notes:
- Upwork reported +95% growth in AI image generation/editing.

### O18 — Content Repurposing

Buyer:
- creators, consultants, podcasts, SMEs with long-form content

Core deliverable:
- convert one source item into shorts, posts, summaries, captions or newsletters

Required capabilities:
- summarization
- editing
- content judgment

Hard disqualifiers:
- weak source fidelity/QA

Cheap validation experiment:
- take one public/owned long-form source and produce a clearly attributed multi-format sample pack

### O19 — AI Workflow Automation

Buyer:
- SMEs with repetitive admin, sales, content or data workflows

Core deliverable:
- working automation with documentation, error handling and handoff

Required capabilities:
- process mapping
- automation tooling
- debugging
- credential/security awareness

Hard disqualifiers:
- no technical implementation evidence
- inability to handle secrets/data safely

Cheap validation experiment:
- build one narrow demo such as lead form -> sheet -> notification using test data and show failure handling

Notes:
- Fiverr reported +125% growth for n8n AI automation; Upwork reported AI integration +178% YoY and strong current interest in AI automation.

### O20 — Chatbot / FAQ Bot Setup

Buyer:
- SMEs, ecommerce sellers, service businesses

Core deliverable:
- scoped FAQ/support bot with knowledge source, fallback behavior and handoff

Required capabilities:
- content structuring
- integration basics
- testing

Hard disqualifiers:
- no capability to validate incorrect answers/escalation behavior

Cheap validation experiment:
- build a demo against a synthetic FAQ set with a documented fallback when information is missing

Notes:
- Upwork reported +71% growth in AI chatbot development.

### O21 — Landing Page / No-code Site Setup

Buyer:
- local businesses, freelancers, events, new offers

Core deliverable:
- simple conversion-focused landing page with contact/CTA and basic analytics where available

Required capabilities:
- layout
- copy structure
- no-code/web tools

Hard disqualifiers:
- no web/no-code capability evidence for live client work

Cheap validation experiment:
- build one sample landing page for a fictional niche and ask target buyers whether it contains enough information to contact/buy

### O22 — AI App / Prototype Implementation

Buyer:
- startups, SMEs, internal innovation teams

Core deliverable:
- scoped working prototype or internal tool, not merely generated code

Required capabilities:
- software development
- testing
- APIs/data handling
- deployment discipline

Hard disqualifiers:
- no coding/product implementation evidence

Cheap validation experiment:
- ship one narrow demo with a real end-to-end workflow and public code/sample documentation

Notes:
- Fiverr reported strong growth in AI mobile/web development and Claude Code-related implementation searches; Upwork shows increasing AI integration demand.

### O23 — Data Annotation / Labeling

Buyer:
- AI/data projects and platforms

Core deliverable:
- accurately labeled/validated data to specification

Required capabilities:
- consistency
- instruction following
- QA

Hard disqualifiers:
- low attention to repetitive detail

Cheap validation experiment:
- complete a small benchmark labeling set and measure agreement/error rate before seeking paid work

Notes:
- Upwork reported +154% YoY growth for AI data annotation/labeling.

### O24 — Tutoring / Explainer Service

Buyer:
- students, professionals, beginners, small teams

Core deliverable:
- 1:1 or small-group explanation/training in a demonstrated area of knowledge

Required capabilities:
- subject knowledge
- explanation ability
- interaction tolerance

Hard disqualifiers:
- no evidence of subject capability
- very low interaction tolerance

Cheap validation experiment:
- offer one 30-minute diagnostic/tutorial session to a narrow audience and collect whether they achieved a defined learning outcome

### O25 — Digital Templates

Buyer:
- consumers or businesses with repeatable document/design needs

Core deliverable:
- reusable template pack

Required capabilities:
- useful workflow/design insight
- packaging
- distribution

Hard disqualifiers:
- urgent first-income requirement with no existing audience/distribution

Cheap validation experiment:
- publish one narrowly useful template and test 20 direct prospects or one marketplace before building a large catalog

Evidence level:
- C because discovery/distribution strongly affects revenue timing.

### O26 — Niche Digital Asset Packs

Buyer:
- creators, designers, small brands, consumers in a specific niche

Core deliverable:
- reusable visual/content asset pack

Required capabilities:
- production quality
- niche relevance
- packaging/distribution

Hard disqualifiers:
- urgent income with no distribution

Cheap validation experiment:
- create a 5-item mini-pack and test direct interest before producing a large collection

Evidence level:
- C due to marketplace/audience dependence.

### O27 — Affiliate Content

Buyer / payer:
- commission is paid by merchant/platform after attributed conversions

Core deliverable:
- content that generates qualified clicks/sales

Required capabilities:
- audience/distribution or strong content acquisition ability
- product-selection judgment
- consistent publishing/testing

Hard disqualifiers:
- urgent predictable income
- no distribution and low content tolerance
- belief that posting alone guarantees commissions

Cheap validation experiment:
- choose one product/problem niche, publish a small controlled content set and measure impressions -> clicks -> qualified actions before scaling

Evidence level:
- C because income is highly distribution/conversion dependent and should not be a generic beginner default.

### O28 — Faceless YouTube Channel

Buyer / payer:
- audience monetization, affiliate, sponsorship or owned offers over time

Core deliverable:
- consistently published channel with valuable content and distribution growth

Required capabilities:
- research
- scripting
- production
- packaging
- persistence

Hard disqualifiers:
- urgent income need
- very low weekly time
- expectation of immediate passive income

Cheap validation experiment:
- produce 3–5 videos in one narrow format and measure retention/click-through signals before committing to a large production system

Evidence level:
- C despite strong Fiverr service demand around YouTube automation, because a creator launching their own channel still bears algorithm/distribution risk and delayed monetization.

## Eligibility Before Ranking

P3 must not simply assign a score to every opportunity.

Hard eligibility rules must run first.

Examples:

- phone-only + complex dashboard work -> ineligible until computer access changes
- camera refusal + offer requires personal on-camera UGC -> exclude that variant
- zero cash tolerance + paid-ad dependent business -> exclude
- urgent 7-day income + audience-dependent product/content path -> heavily penalize or exclude from primary recommendation
- low customer-interaction tolerance + appointment setting -> exclude
- unknown skill + high-skill technical implementation -> exclude until capability verification
- weak language proficiency + professional translation -> exclude

The system should explain exclusions using the user's own P1 evidence rather than presenting them as opaque AI decisions.

## P2 Coverage Check

The v0 library intentionally contains multiple economic models:

- direct services
- productized services
- operational support
- technical implementation
- creative production
- product-based income
- content/distribution-based income
- platform/task work

It also intentionally contains opportunities with very different:

- startup cost
- revenue speed
- interaction level
- camera/public-presence requirement
- device requirement
- skill threshold
- recurring potential
- scalability
- distribution risk

This prevents the future scoring engine from choosing among near-duplicates only.

## P2 Acceptance Gate

P2 passes when:

- at least 20 meaningfully distinct opportunities exist
- every opportunity has the normalized metadata needed for eligibility and later ranking
- opportunities cover service, product, content, operational and technical paths
- urgent-income and long-horizon opportunities are distinguishable
- customer interaction and public-presence requirements are explicit
- device/budget/capability disqualifiers are explicit
- every opportunity has a cheap validation experiment
- current-demand claims have evidence quality labels
- distribution-dependent paths are not mislabeled as fast or predictable income
- no personalized ranking is performed yet

## P2 Fail Conditions

P2 fails if:

- most entries are merely variations of affiliate/content/digital products
- demand is assigned from LLM intuition without evidence quality
- a path can appear suitable despite violating a P1 hard constraint
- startup cost or time-to-revenue is omitted
- opportunities promise or imply guaranteed income
- the library starts ranking specific people before P3 exists

## Handoff to P3

After P2 passes and owner approval is given, P3 should define:

`Eligibility + Opportunity Scoring v0`

P3 should apply:

1. hard eligibility filters
2. weighted opportunity scoring
3. confidence reduction for weak/unknown capabilities
4. explanation of why the top path fits
5. explanation of why tempting alternatives were rejected

P3 must not treat popularity as fit.

## Locked Statement

SoloForge is not trying to answer:

> What are the best ways to make money online?

It is building toward:

> Given this person's actual constraints, evidence and market access, which income experiment has the highest probability of being worth testing first?
