# SoloForge Income Engine — P2 Opportunity Library v0

Status: Validated — PASS

Date: 2026-09-04

## Purpose

P2 defines a controlled library of income opportunities that later phases can match against the evidence-backed user profiles produced by P1.

The library exists to prevent a language model from inventing popular online-income ideas on demand and sending different users toward the same generic paths.

P2 does **not** rank opportunities for a person. Personalized eligibility and ranking belong to P3.

## Product Principle

SoloForge should reduce wrong experiments, not merely produce more ideas.

Every opportunity must state what is sold, who buys it, what the user needs, how customers are acquired, how difficult acquisition is structurally, how quickly first revenue could plausibly occur, what can disqualify the path, and what the cheapest sensible validation experiment is.

## Evidence Policy

Market demand must not be guessed from LLM familiarity.

Demand-evidence levels:

- `A`: current explicit evidence — recent marketplace or business-demand evidence directly supports the service category or a very close implementation category.
- `B`: durable workflow demand — recurring business workflow with credible current demand, but without a precise recent category-growth figure in this evidence set.
- `C`: distribution-dependent — monetization depends heavily on audience, algorithms, marketplace discovery, or delayed compounding and must not be treated as a fast-income default.

Demand evidence is directional. It is **not** a guarantee of client availability, pricing, conversion, or income.

## Current Market Evidence Used for v0

1. Upwork, `In-Demand Skills 2026`
   - AI video generation/editing +329% YoY
   - AI integration +178%
   - AI data annotation/labeling +154%
   - AI image generation/editing +95%
   - AI chatbot development +71%
   - continued hiring in data analytics, graphic design, virtual assistance, web work, lead generation and human-led operational work
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

## P2 Completeness Audit

Audit date: 2026-09-04

The first P2 draft contained enough opportunity variety but was not yet machine-safe for P3. The audit found four metadata gaps:

1. `acquisition_modes` was explicit only for some entries.
2. Several scalar fields used mixed values such as `fast-short`, `medium-high`, `zero-very_low`, and `A/B`, which are unsuitable for deterministic eligibility/scoring.
3. `minimum_device` was not explicit for every opportunity.
4. Two fields needed by the intended P3 decision model were missing from the contract: `acquisition_difficulty` and `margin_profile`.

All four gaps are closed in this version.

## Canonical Metadata Contract

Every opportunity must contain these required fields:

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
acquisition_difficulty
margin_profile
recurring_revenue_potential
scalability
ai_leverage
market_demand_signal
evidence_level
hard_disqualifiers
cheap_validation_experiment
```

`notes` is optional and must never be required for P3 eligibility or ranking.

### Canonical enums

`startup_cost_band`
- `zero`
- `very_low`
- `low`
- `moderate`
- `capital_required`

`time_to_first_revenue`
- `fast` — plausibly test/sell within 7 days when required skill and outreach are already present
- `short` — 8–30 days
- `medium` — 1–3 months
- `long` — more than 3 months or strongly distribution-dependent

`minimum_device`
- `phone_ok`
- `computer_preferred`
- `computer_required`
- `production_capable_device`

`customer_interaction`
- `low`
- `medium`
- `high`

`public_presence`
- `none`
- `voice_optional`
- `camera_optional`
- `camera_preferred`

`acquisition_difficulty`
- `low`
- `medium`
- `high`

`margin_profile`
- `low`
- `medium`
- `high`

`recurring_revenue_potential`
- `low`
- `medium`
- `high`

`scalability`
- `low`
- `medium`
- `high`

`ai_leverage`
- `assistive`
- `strong`
- `core`

`market_demand_signal`
- `current_growth`
- `durable_workflow`
- `distribution_dependent`

`evidence_level`
- `A`
- `B`
- `C`

No composite scalar values are allowed in P2 canonical metadata.

### Acquisition mode tags

P2 uses controlled tags so P3 can compare a user's actual market access against the path:

- `direct_outreach`
- `freelance_marketplace`
- `professional_network`
- `local_business_network`
- `creator_community`
- `ecommerce_community`
- `agency_partnership`
- `platform_marketplace`
- `education_community`
- `owned_audience`
- `algorithmic_distribution`
- `referrals`

### Margin profile rule

`margin_profile` is a structural heuristic for direct delivery costs, not a verified market-price or net-profit estimate. It excludes the user's labor/time and must not be presented as promised profitability.

### Acquisition difficulty rule

`acquisition_difficulty` describes structural difficulty of reaching and converting a buyer for a new entrant with no special distribution advantage. P3 may adjust effective difficulty when P1 shows existing customers, audience, network, or platform access.

## Opportunity Library v0 — Canonical Records

### O01 — Spreadsheet Data Cleanup
- model_type: `service`
- buyer: SMEs, ecommerce sellers, offices, agencies with messy operational spreadsheets
- core_deliverable: cleaned, deduplicated, standardized spreadsheet with validation/reconciliation notes
- startup_cost_band: `zero`
- time_to_first_revenue: `fast`
- required_capabilities: spreadsheet fluency; attention to detail; basic data reasoning
- minimum_device: `computer_required`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `professional_network`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: phone-only for non-trivial files; no practical spreadsheet evidence until skill verification
- cheap_validation_experiment: create one synthetic before/after cleanup sample and offer a fixed-scope cleanup to 10–20 prospects

### O02 — PDF / Document to Spreadsheet Conversion
- model_type: `service`
- buyer: offices, logistics teams, sellers, finance/admin teams needing structured extraction
- core_deliverable: accurate structured Excel/Sheets output from PDFs/forms/documents with manual QA
- startup_cost_band: `zero`
- time_to_first_revenue: `fast`
- required_capabilities: careful checking; spreadsheet basics; document handling
- minimum_device: `computer_preferred`
- customer_interaction: `low`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `professional_network`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `low`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: unwillingness to perform manual QA
- cheap_validation_experiment: build a 3-page sample conversion showing source document versus validated spreadsheet output

### O03 — Dashboard & Business Reporting
- model_type: `service`
- buyer: SMEs and managers with recurring sales/operations data
- core_deliverable: recurring dashboard/report with defined KPIs and data-refresh process
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: spreadsheet/data reasoning; dashboard tool familiarity; stakeholder clarification
- minimum_device: `computer_required`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `professional_network`, `freelance_marketplace`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: no evidence of data/reporting capability
- cheap_validation_experiment: create one niche-specific demo dashboard from public/synthetic data and ask 10 target businesses whether the KPIs support real weekly decisions

### O04 — Virtual Admin / Operations Assistant
- model_type: `service`
- buyer: founders, small teams, online sellers, professionals
- core_deliverable: scheduling, follow-up, document handling, order/admin coordination and routine operations
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: reliability; organization; written communication
- minimum_device: `computer_preferred`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `professional_network`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `medium`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `assistive`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: extremely low customer-interaction tolerance; highly inconsistent availability for response-sensitive work
- cheap_validation_experiment: offer a one-week fixed-scope admin cleanup/follow-up package to a small business or professional contact

### O05 — Customer Support / Inbox Management
- model_type: `service`
- buyer: ecommerce sellers, service businesses, creators, SMEs
- core_deliverable: response handling, FAQ support, order follow-up and escalation notes
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: communication; patience; process discipline
- minimum_device: `phone_ok`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `ecommerce_community`, `freelance_marketplace`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `medium`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `assistive`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: low interaction tolerance; inability to maintain agreed response windows
- cheap_validation_experiment: build a sample FAQ + response workflow for one business category and pitch a limited inbox-coverage trial

### O06 — Lead Research / Prospect List Building
- model_type: `service`
- buyer: B2B sellers, agencies, consultants, recruiters
- core_deliverable: researched target list with defined qualification fields
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: research; structured data handling; judgment against criteria
- minimum_device: `computer_required`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `agency_partnership`, `professional_network`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: weak research discipline; no computer for larger research tasks
- cheap_validation_experiment: produce 20 sample prospects for one narrow buyer profile and ask a seller to rate relevance

### O07 — Outreach / Appointment Setting Support
- model_type: `service`
- buyer: local businesses, agencies, consultants, B2B service providers
- core_deliverable: prospect outreach, follow-up and qualified appointment booking
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: customer interaction tolerance; sales resilience; clear written/voice communication
- minimum_device: `phone_ok`
- customer_interaction: `high`
- public_presence: `voice_optional`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `agency_partnership`, `professional_network`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `assistive`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: low sales/customer-contact tolerance
- cheap_validation_experiment: run a 20-prospect manual outreach test for one clear offer and record reply rate, interest and objections

### O08 — Presentation & Document Formatting
- model_type: `service`
- buyer: students, professionals, SMEs, consultants, authors
- core_deliverable: polished slides/documents with layout cleanup and consistency
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: visual organization; document tools; careful editing
- minimum_device: `computer_preferred`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `freelance_marketplace`, `education_community`, `professional_network`, `direct_outreach`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: no evidence of document/presentation capability for higher-complexity work
- cheap_validation_experiment: publish three before/after examples from synthetic documents/slides

### O09 — Translation / Localization
- model_type: `service`
- buyer: creators, ecommerce sellers, websites, SMEs, publishers
- core_deliverable: translated/localized copy with human review and contextual adaptation
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: strong language proficiency; nuance; QA
- minimum_device: `computer_preferred`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `freelance_marketplace`, `direct_outreach`, `professional_network`, `creator_community`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `assistive`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: weak target-language proficiency; raw machine translation without human review
- cheap_validation_experiment: create a side-by-side localization sample for one product page or short-video script

### O10 — Short-form Video Editing
- model_type: `service`
- buyer: creators, ecommerce sellers, SMEs, agencies
- core_deliverable: vertical short video ready to post, including pacing/cuts/captions where scoped
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: editing workflow; storytelling/pacing; visual QA
- minimum_device: `production_capable_device`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `creator_community`, `agency_partnership`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: device incapable of required editing workload
- cheap_validation_experiment: edit three samples from licensed/self-created footage and pitch a fixed five-video starter pack

### O11 — AI UGC / Ad Creative Production
- model_type: `service`
- buyer: ecommerce brands, agencies, advertisers
- core_deliverable: creator-style ad concepts/videos produced with AI and human QA
- startup_cost_band: `low`
- time_to_first_revenue: `short`
- required_capabilities: ad concept judgment; script/pacing; AI video workflow; claim/brand-safety QA
- minimum_device: `production_capable_device`
- customer_interaction: `medium`
- public_presence: `camera_optional`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `agency_partnership`, `ecommerce_community`
- acquisition_difficulty: `high`
- margin_profile: `medium`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `core`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: inability to review claims/brand safety; insufficient production-tool access
- cheap_validation_experiment: create two spec ads for a fictional or owned product and ask 5–10 marketers/sellers which hook they would test

### O12 — Social Media Content Pack
- model_type: `productized_service`
- buyer: local SMEs, solo businesses, ecommerce sellers
- core_deliverable: recurring bundle of posts, short scripts, visual assets and captions for defined channels
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: content planning; basic visual/copy judgment; client communication
- minimum_device: `computer_preferred`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `local_business_network`, `professional_network`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: inability to maintain a consistent delivery cadence
- cheap_validation_experiment: make a seven-day sample pack for one niche and offer it to 10 businesses in that niche

### O13 — Canva Social Design
- model_type: `service`
- buyer: SMEs, creators, ecommerce sellers, event/community operators
- core_deliverable: repeatable branded social graphics/templates
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: visual design; Canva fluency
- minimum_device: `production_capable_device`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `local_business_network`, `creator_community`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: tool exposure without evidence must not qualify the user for advanced design work
- cheap_validation_experiment: create one six-post visual set for a sample brand and seek feedback/orders from a defined niche

### O14 — YouTube Thumbnail Design
- model_type: `service`
- buyer: YouTubers, agencies, media teams
- core_deliverable: clickable, brand-consistent thumbnails
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: visual composition; image editing; packaging judgment
- minimum_device: `production_capable_device`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `creator_community`, `agency_partnership`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: no portfolio/evidence of visual capability
- cheap_validation_experiment: redesign three public thumbnails as non-commercial portfolio exercises and contact 10 channels with one tailored sample

### O15 — E-commerce Listing Optimization
- model_type: `service`
- buyer: marketplace sellers and small ecommerce brands
- core_deliverable: improved titles, descriptions, image order, attributes, benefit structure and listing QA
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: copy/research; product understanding; platform familiarity
- minimum_device: `computer_preferred`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `ecommerce_community`, `freelance_marketplace`, `professional_network`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: no relevant platform access or inability to evaluate product claims accurately
- cheap_validation_experiment: rewrite one weak listing into a before/after sample and ask sellers to evaluate clarity and conversion relevance

### O16 — Marketplace Store Operations Support
- model_type: `service`
- buyer: small ecommerce sellers
- core_deliverable: listing updates, order/admin follow-up, campaign support and catalog maintenance
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: operational discipline; platform familiarity; customer communication
- minimum_device: `computer_preferred`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `ecommerce_community`, `professional_network`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `medium`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `assistive`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: inability to maintain agreed response/service windows
- cheap_validation_experiment: offer one fixed catalog-cleanup or listing-maintenance session instead of a vague VA package

### O17 — AI Product Visual / Image Editing
- model_type: `service`
- buyer: ecommerce sellers, local brands, creators
- core_deliverable: cleaned/enhanced product visuals, background variations and ad-ready compositions under authenticity rules
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: image judgment; AI/image editing tools; QA
- minimum_device: `production_capable_device`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `ecommerce_community`, `owned_audience`
- acquisition_difficulty: `medium`
- margin_profile: `medium`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `core`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: inability to avoid misleading product representation
- cheap_validation_experiment: create three before/after examples using owned or permitted product images and pitch a five-image starter pack

### O18 — Content Repurposing
- model_type: `productized_service`
- buyer: creators, consultants, podcasts, SMEs with long-form content
- core_deliverable: convert one source item into shorts, posts, summaries, captions or newsletters
- startup_cost_band: `very_low`
- time_to_first_revenue: `short`
- required_capabilities: summarization; editing; content judgment; source fidelity
- minimum_device: `computer_preferred`
- customer_interaction: `medium`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `creator_community`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: weak source fidelity/QA
- cheap_validation_experiment: take one public/owned long-form source and produce a clearly attributed multi-format sample pack

### O19 — AI Workflow Automation
- model_type: `service`
- buyer: SMEs with repetitive admin, sales, content or data workflows
- core_deliverable: working automation with documentation, error handling and handoff
- startup_cost_band: `low`
- time_to_first_revenue: `medium`
- required_capabilities: process mapping; automation tooling; debugging; credential/security awareness
- minimum_device: `computer_required`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `professional_network`, `agency_partnership`, `freelance_marketplace`, `referrals`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `core`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: no technical implementation evidence; inability to handle secrets/data safely
- cheap_validation_experiment: build one narrow demo such as lead form -> sheet -> notification using test data and show failure handling

### O20 — Chatbot / FAQ Bot Setup
- model_type: `service`
- buyer: SMEs, ecommerce sellers, service businesses
- core_deliverable: scoped FAQ/support bot with knowledge source, fallback behavior and human handoff
- startup_cost_band: `low`
- time_to_first_revenue: `medium`
- required_capabilities: content structuring; integration basics; testing; fallback design
- minimum_device: `computer_required`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `professional_network`, `agency_partnership`, `freelance_marketplace`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `medium`
- ai_leverage: `core`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: no capability to validate incorrect answers or escalation behavior
- cheap_validation_experiment: build a demo against a synthetic FAQ set with a documented fallback when information is missing

### O21 — Landing Page / No-code Site Setup
- model_type: `service`
- buyer: local businesses, freelancers, events, new offers
- core_deliverable: simple conversion-focused landing page with contact/CTA and basic analytics where available
- startup_cost_band: `low`
- time_to_first_revenue: `medium`
- required_capabilities: layout; copy structure; no-code/web tools
- minimum_device: `computer_required`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `local_business_network`, `professional_network`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `strong`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: no web/no-code capability evidence for live client work
- cheap_validation_experiment: build one sample landing page for a fictional niche and ask target buyers whether it contains enough information to contact/buy

### O22 — AI App / Prototype Implementation
- model_type: `service`
- buyer: startups, SMEs, internal innovation teams
- core_deliverable: scoped working prototype or internal tool, not merely generated code
- startup_cost_band: `moderate`
- time_to_first_revenue: `medium`
- required_capabilities: software development; testing; APIs/data handling; deployment discipline
- minimum_device: `computer_required`
- customer_interaction: `high`
- public_presence: `none`
- acquisition_modes: `direct_outreach`, `freelance_marketplace`, `professional_network`, `agency_partnership`, `referrals`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `medium`
- ai_leverage: `core`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: no coding/product implementation evidence
- cheap_validation_experiment: ship one narrow demo with a real end-to-end workflow and public code/sample documentation

### O23 — Data Annotation / Labeling
- model_type: `platform_work`
- buyer: AI/data projects, vendors and platforms
- core_deliverable: accurately labeled/validated data to specification
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: consistency; instruction following; QA; attention to repetitive detail
- minimum_device: `computer_preferred`
- customer_interaction: `low`
- public_presence: `none`
- acquisition_modes: `platform_marketplace`, `freelance_marketplace`, `professional_network`
- acquisition_difficulty: `medium`
- margin_profile: `low`
- recurring_revenue_potential: `low`
- scalability: `low`
- ai_leverage: `assistive`
- market_demand_signal: `current_growth`
- evidence_level: `A`
- hard_disqualifiers: low attention to repetitive detail; inability to follow labeling specifications consistently
- cheap_validation_experiment: complete a small benchmark labeling set and measure agreement/error rate before seeking paid work

### O24 — Tutoring / Explainer Service
- model_type: `service`
- buyer: students, professionals, beginners, small teams
- core_deliverable: 1:1 or small-group explanation/training in a demonstrated area of knowledge
- startup_cost_band: `zero`
- time_to_first_revenue: `short`
- required_capabilities: subject knowledge; explanation ability; interaction tolerance
- minimum_device: `phone_ok`
- customer_interaction: `high`
- public_presence: `voice_optional`
- acquisition_modes: `education_community`, `professional_network`, `local_business_network`, `platform_marketplace`, `referrals`
- acquisition_difficulty: `medium`
- margin_profile: `high`
- recurring_revenue_potential: `high`
- scalability: `low`
- ai_leverage: `assistive`
- market_demand_signal: `durable_workflow`
- evidence_level: `B`
- hard_disqualifiers: no evidence of subject capability; very low interaction tolerance
- cheap_validation_experiment: offer one 30-minute diagnostic/tutorial session to a narrow audience and measure a defined learning outcome

### O25 — Digital Templates
- model_type: `product`
- buyer: consumers or businesses with repeatable document/design needs
- core_deliverable: reusable template pack
- startup_cost_band: `very_low`
- time_to_first_revenue: `long`
- required_capabilities: useful workflow/design insight; packaging; distribution
- minimum_device: `production_capable_device`
- customer_interaction: `low`
- public_presence: `none`
- acquisition_modes: `platform_marketplace`, `direct_outreach`, `owned_audience`, `algorithmic_distribution`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `high`
- ai_leverage: `strong`
- market_demand_signal: `distribution_dependent`
- evidence_level: `C`
- hard_disqualifiers: urgent first-income requirement with no existing audience/distribution
- cheap_validation_experiment: publish one narrowly useful template and test 20 direct prospects or one marketplace before building a large catalog

### O26 — Niche Digital Asset Packs
- model_type: `product`
- buyer: creators, designers, small brands, consumers in a specific niche
- core_deliverable: reusable visual/content asset pack
- startup_cost_band: `very_low`
- time_to_first_revenue: `long`
- required_capabilities: production quality; niche relevance; packaging; distribution
- minimum_device: `production_capable_device`
- customer_interaction: `low`
- public_presence: `none`
- acquisition_modes: `platform_marketplace`, `creator_community`, `owned_audience`, `algorithmic_distribution`
- acquisition_difficulty: `high`
- margin_profile: `high`
- recurring_revenue_potential: `medium`
- scalability: `high`
- ai_leverage: `strong`
- market_demand_signal: `distribution_dependent`
- evidence_level: `C`
- hard_disqualifiers: urgent income requirement with no distribution
- cheap_validation_experiment: create a five-item mini-pack and test direct interest before producing a large collection

### O27 — Affiliate Content
- model_type: `content_commission`
- buyer: merchant/platform pays commission after attributed conversion; audience is the acquisition target
- core_deliverable: content that generates qualified clicks and attributed conversions
- startup_cost_band: `low`
- time_to_first_revenue: `long`
- required_capabilities: audience/distribution or strong content acquisition ability; product-selection judgment; consistent publishing/testing
- minimum_device: `phone_ok`
- customer_interaction: `low`
- public_presence: `camera_optional`
- acquisition_modes: `owned_audience`, `algorithmic_distribution`, `creator_community`
- acquisition_difficulty: `high`
- margin_profile: `medium`
- recurring_revenue_potential: `medium`
- scalability: `high`
- ai_leverage: `strong`
- market_demand_signal: `distribution_dependent`
- evidence_level: `C`
- hard_disqualifiers: urgent predictable-income need; no distribution plus low content tolerance; belief that posting guarantees commissions
- cheap_validation_experiment: choose one product/problem niche, publish a small controlled content set and measure impressions -> clicks -> qualified actions before scaling

### O28 — Faceless YouTube Channel
- model_type: `content_media_asset`
- buyer: audience monetization, affiliate, sponsorship or owned offers over time
- core_deliverable: consistently published channel with valuable content and distribution growth
- startup_cost_band: `moderate`
- time_to_first_revenue: `long`
- required_capabilities: research; scripting; production; packaging; persistence
- minimum_device: `production_capable_device`
- customer_interaction: `low`
- public_presence: `none`
- acquisition_modes: `algorithmic_distribution`, `owned_audience`, `creator_community`
- acquisition_difficulty: `high`
- margin_profile: `medium`
- recurring_revenue_potential: `medium`
- scalability: `high`
- ai_leverage: `strong`
- market_demand_signal: `distribution_dependent`
- evidence_level: `C`
- hard_disqualifiers: urgent income need; very low weekly time; expectation of immediate passive income
- cheap_validation_experiment: produce 3–5 videos in one narrow format and measure retention/click-through signals before committing to a large production system

## Eligibility Before Ranking

P3 must not simply assign a score to every opportunity. Hard eligibility rules run first.

Examples:

- phone-only + complex dashboard work -> ineligible until computer access changes
- camera refusal + a specific offer variant requires on-camera UGC -> exclude that variant
- zero cash tolerance + a capital-dependent path -> exclude
- urgent 7-day income + distribution-dependent product/content path -> exclude from primary recommendation unless strong existing distribution materially changes the evidence
- low customer-interaction tolerance + appointment setting -> exclude
- unknown skill + high-skill technical implementation -> exclude until capability verification
- weak language proficiency + professional translation -> exclude

The system must explain exclusions using the user's own P1 evidence rather than opaque AI judgment.

## P2 Validation / Completeness Results

| Criterion | Result |
| --- | --- |
| At least 20 meaningfully distinct opportunities | PASS — 28 |
| Required metadata present for all opportunities | PASS |
| `acquisition_modes` explicit for all 28 | PASS |
| `minimum_device` explicit for all 28 | PASS |
| Acquisition difficulty explicit for all 28 | PASS |
| Margin profile explicit for all 28 | PASS |
| No mixed scalar enum values | PASS |
| Service/product/content/operational/technical coverage | PASS |
| Fast versus long-horizon paths distinguishable | PASS |
| Interaction/public-presence requirements explicit | PASS |
| Device/budget/capability disqualifiers explicit | PASS |
| Cheap validation experiment present for all 28 | PASS |
| Demand signal + evidence level present for all 28 | PASS |
| Distribution-dependent paths not labeled fast/predictable | PASS |
| No personalized ranking performed | PASS |

## P2 Conclusion

**P2 PASS**

The Opportunity Library now has enough normalized, deterministic metadata for P3 to perform hard eligibility filtering before any weighted ranking.

P2 does not claim that these opportunities are equally attractive, that the demand evidence guarantees paid work, or that the structural margin/acquisition heuristics are measured conversion data. Those questions belong to later market validation and outcome learning.

## Handoff to P3

After owner approval, P3 should define:

`Eligibility + Opportunity Scoring v0`

P3 must apply in this order:

1. hard eligibility filters
2. confidence-aware capability matching
3. weighted opportunity scoring
4. explanation of why the top path fits
5. explanation of why tempting alternatives were rejected
6. cheap experiment selection

P3 must not treat popularity as fit and must not override P1 hard constraints merely because an opportunity has strong market-demand evidence.

## Locked Statement

SoloForge is not trying to answer:

> What are the best ways to make money online?

It is building toward:

> Given this person's actual constraints, evidence and market access, which income experiment has the highest probability of being worth testing first?
