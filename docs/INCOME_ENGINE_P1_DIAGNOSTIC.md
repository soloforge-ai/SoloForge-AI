# SoloForge Income Engine — P1 Income Diagnostic v0

Status: Validated — PASS

Date: 2026-09-04

## Purpose

P1 defines the minimum diagnostic needed to understand a person well enough to support later income-path recommendations without falling back to generic advice such as affiliate marketing, TikTok, digital products, or freelancing for everyone.

P1 is a discovery and validation phase. It does not build a new Flutter screen, recommendation engine, marketplace, billing system, or automated income guarantee.

## Product Hypothesis

A useful income recommendation requires more than asking what the user wants to do.

The diagnostic should infer practical capability, constraints, urgency, working style, available assets, and willingness to sell from questions that a beginner can answer even when they do not know their own skills yet.

The output of P1 is a normalized user profile that P2 can score against an Opportunity Library.

## P1 Success Condition

P1 passes only if the same diagnostic can produce meaningfully different profiles for different users and preserve enough evidence for later recommendation decisions.

It must not recommend an income path yet.

## Diagnostic Questions

### Q1 — Income goal

What additional monthly income would make a meaningful difference to you?

Capture:
- target monthly income
- whether the target is optional, important, or urgent

### Q2 — Time to first money

How soon do you need the first real income result?

Options:
- within 7 days
- within 30 days
- within 3 months
- longer than 3 months is acceptable

Capture:
- revenue urgency

### Q3 — Available time

How much focused time can you realistically spend?

Capture:
- hours per weekday
- hours per weekend
- schedule consistency

### Q4 — Starting budget

How much can you afford to invest before earning anything back?

Capture:
- zero / very low / moderate / flexible budget
- maximum acceptable loss

### Q5 — Devices and access

What can you reliably use?

Possible answers:
- Android phone
- iPhone
- Windows computer
- Mac
- tablet / iPad
- stable internet

Capture:
- available production capability
- device constraints

### Q6 — Tool familiarity

Which tools have you actually used before, even at a basic level?

Examples:
- Excel / Google Sheets
- Canva
- CapCut
- TikTok
- Facebook / Instagram
- ChatGPT or other AI tools
- Power BI
- coding tools
- e-commerce platforms

Capture:
- observed tool familiarity, not claimed expertise

### Q7 — Past helpful behavior

What do other people usually ask you to help with?

Examples:
- fixing documents
- organizing information
- explaining things
- taking photos
- writing
- selling
- editing videos
- spreadsheets
- technology setup
- planning

Capture:
- evidence-based skill signals

### Q8 — Preferred work mode

Which type of work feels least difficult for you?

Options may include:
- organizing data
- writing
- speaking
- visual design
- researching
- teaching
- selling
- operating tools
- solving technical problems
- repetitive operational work
- not sure

Capture:
- preferred cognitive/work mode

### Q9 — Customer interaction tolerance

How comfortable are you talking to customers or strangers?

Capture:
- direct sales tolerance
- support tolerance
- preference for asynchronous work

### Q10 — Camera / public presence

Are you willing to show your face or voice publicly?

Capture separately:
- face on camera
- voice only
- text only
- anonymous brand acceptable

### Q11 — Existing assets

Do you already have anything that could help you earn?

Examples:
- product inventory
- existing customers
- audience or followers
- Facebook page
- TikTok account
- portfolio
- professional experience
- community access
- specialist knowledge

Capture:
- distribution assets
- credibility assets
- monetizable assets

### Q12 — Sales preference

Which feels more acceptable?

Options:
- selling a service directly to clients
- selling a product repeatedly
- creating content and monetizing later
- commission / affiliate income
- building something that earns slowly over time
- not sure

Capture:
- business-model tolerance, not final recommendation

### Q13 — Risk tolerance

Which trade-off fits you best?

Examples:
- I prefer fast and predictable income even if it is less scalable
- I can tolerate uncertain income for higher upside
- I prefer to invest almost no money
- I can invest money to save time

Capture:
- risk profile
- speed-versus-scale preference

### Q14 — Language and market reach

Which languages can you work or sell in, and which markets can you realistically reach?

Capture:
- language ability
- local vs global reach
- existing market access

### Q15 — Unknown-skill fallback

If the user answers that they do not know what they are good at, do not force them to choose a skill.

Mark:
- `skill_confidence = low`
- `diagnostic_mode = skill_discovery`

P2 or a later validation phase may use small practical tasks to infer capability.

## Beginner-Safe Design Rule

The diagnostic must never require a beginner to know business terminology, job categories, or their own professional skill label.

Prefer behavior questions such as:

- What do people ask you to help with?
- Which tools have you used?
- Which task feels easiest?
- Are you comfortable talking to customers?

Avoid relying on:

- What is your niche?
- What business model do you want?
- What is your competitive advantage?
- What are your monetizable skills?

Those can be inferred later.

## Normalized P1 Output

P1 should produce a structured profile containing at least:

```text
income_goal
revenue_urgency
available_time
starting_budget
maximum_loss_tolerance
devices
internet_access
tool_familiarity
observed_skill_signals
preferred_work_modes
customer_interaction_tolerance
camera_tolerance
voice_tolerance
existing_assets
distribution_assets
sales_model_preferences
risk_tolerance
speed_vs_scale_preference
languages
market_reach
skill_confidence
diagnostic_mode
unknowns
```

## Evidence Rule

Each inferred field must retain the user answer or behavioral evidence that produced it.

Example:

```text
Signal: spreadsheet capability
Evidence: user reports coworkers regularly ask them to fix Excel files
Confidence: medium
```

Do not turn a weak signal into a hard fact.

## What P1 Must Not Do

P1 must not:

- recommend a business or income path
- claim guaranteed income
- rank opportunities
- invent user skills
- infer high skill from tool exposure alone
- push every beginner toward affiliate, content creation, or digital products
- add Flutter UI
- add Supabase schema
- add billing
- add autonomous agents
- add external scraping
- add paid AI generation

## Validation Test

Before P1 can be considered complete, run the same diagnostic against 10 deliberately different test personas.

The personas must include at least:

1. Data / spreadsheet-oriented person
2. Strong speaker with social-media familiarity
3. Visual creator who dislikes customer interaction
4. Existing small seller
5. Beginner with no identified skill
6. Student with low budget
7. Full-time worker with little available time
8. Unemployed person with substantial available time
9. Person with money but little time
10. Person with almost no money but strong willingness to work

## P1 Pass Criteria

P1 passes when:

- all 10 personas can complete the questions without requiring expert terminology
- the normalized profiles are materially different where the inputs are different
- unknown skills remain unknown instead of being fabricated
- hard constraints such as time, budget, camera tolerance, urgency, and devices are preserved
- every inferred capability has traceable evidence
- no income recommendation is generated yet
- the output is sufficient for P2 Opportunity Library + scoring work

## P1 Fail Criteria

P1 fails if:

- most users collapse into the same generic profile
- beginners are forced to self-identify skills they do not understand
- the diagnostic ignores urgent income needs or execution constraints
- inferred skills are presented as facts without evidence
- the output cannot distinguish service-first, product-first, content-first, or skill-discovery users
- the system starts recommending before the opportunity model exists

# P1 Validation Results — 10 Personas

Validation date: 2026-09-04

No income opportunity was recommended during this test. The test only evaluated whether the diagnostic produces distinct, evidence-backed user profiles.

## Persona 1 — Data / spreadsheet oriented

Normalized profile highlights:
- income goal: THB 8,000/month, important
- revenue urgency: within 30 days
- available time: 2 hours weekdays, 6 hours weekends
- starting budget: very low, maximum loss THB 500
- devices: Windows PC + Android + stable internet
- tool familiarity: Excel, Google Sheets, Power BI, ChatGPT
- preferred work mode: organizing data, solving structured problems
- customer interaction tolerance: low-to-medium; asynchronous preferred
- camera tolerance: no
- existing assets: professional office experience
- sales-model tolerance: direct service acceptable if communication can be mostly asynchronous
- risk: low; speed preferred over long-term scale
- languages/market reach: Thai, basic working English
- skill confidence: high
- diagnostic mode: standard

Evidence trace:
- spreadsheet capability: coworkers regularly ask for help fixing formulas, cleaning sheets, and checking totals — confidence high
- reporting capability: has built recurring Power BI reports at work — confidence medium-to-high

## Persona 2 — Strong speaker with social-media familiarity

Normalized profile highlights:
- income goal: THB 10,000/month, important
- revenue urgency: within 30 days
- available time: 4 hours/day
- starting budget: low, maximum loss THB 1,000
- devices: Android phone + stable internet
- tool familiarity: TikTok, Facebook, CapCut, Canva, ChatGPT
- preferred work mode: speaking, selling, explaining
- customer interaction tolerance: high
- camera tolerance: yes
- voice tolerance: yes
- existing assets: active social accounts and small existing audience
- sales-model tolerance: service or content acceptable
- risk: medium
- languages/market reach: Thai
- skill confidence: medium-to-high
- diagnostic mode: standard

Evidence trace:
- speaking/presentation signal: friends repeatedly ask this person to present, host live sessions, and explain products — confidence high
- social-media production signal: regularly records and edits short videos — confidence medium

## Persona 3 — Visual creator who dislikes customer interaction

Normalized profile highlights:
- income goal: THB 5,000/month, optional-to-important
- revenue urgency: within 3 months
- available time: 3 hours/day
- starting budget: low
- devices: iPad + Android + stable internet
- tool familiarity: Procreate, Canva, basic CapCut, ChatGPT
- preferred work mode: visual design, illustration
- customer interaction tolerance: low
- camera tolerance: no
- voice tolerance: no preference / low
- existing assets: small illustration portfolio
- sales-model tolerance: repeatable product preferred over direct client selling
- risk: medium
- languages/market reach: Thai, basic English
- skill confidence: high
- diagnostic mode: standard

Evidence trace:
- visual capability: has a portfolio and people request poster/illustration help — confidence high
- direct-sales tolerance remains low by explicit answer; this is a constraint, not a skill inference

## Persona 4 — Existing small seller

Normalized profile highlights:
- income goal: THB 15,000/month additional, important
- revenue urgency: within 30 days
- available time: 2 hours/day outside existing operations
- starting budget: moderate
- devices: Android phone + Windows PC + stable internet
- tool familiarity: Facebook, TikTok, marketplace seller tools, Canva, basic Sheets
- preferred work mode: selling, operations, customer follow-up
- customer interaction tolerance: high
- camera tolerance: medium; voice acceptable
- existing assets: inventory, existing buyers, Facebook page, marketplace account
- distribution assets: existing customer base and social page
- sales-model tolerance: product sales strongly preferred
- risk: medium
- languages/market reach: Thai/local market
- skill confidence: medium-to-high
- diagnostic mode: standard

Evidence trace:
- sales/operations capability: already handles orders, customer questions, fulfillment, and repeat buyers — confidence high
- content capability: only basic tool exposure; not upgraded to high skill

## Persona 5 — Beginner with no identified skill

Normalized profile highlights:
- income goal: THB 3,000/month, important
- revenue urgency: within 30 days
- available time: 4 hours/day
- starting budget: zero
- devices: Android phone + stable internet
- tool familiarity: basic Facebook, basic ChatGPT
- observed skill signals: none strong enough to classify
- preferred work mode: not sure
- customer interaction tolerance: medium
- camera tolerance: no
- existing assets: none identified
- sales-model tolerance: not sure
- risk: low; cannot afford meaningful loss
- languages/market reach: Thai
- skill confidence: low
- diagnostic mode: skill_discovery
- unknowns: practical capability, preferred work mode, sales-model fit

Evidence trace:
- no capability is promoted from weak tool exposure
- unknown skill remains unknown instead of being converted into a generic creator/affiliate profile

## Persona 6 — Student with low budget

Normalized profile highlights:
- income goal: THB 4,000/month, important
- revenue urgency: within 3 months
- available time: 2 hours weekdays, 6 hours weekends
- starting budget: very low, maximum loss THB 100
- devices: Android + shared Windows PC + stable internet
- tool familiarity: Canva, CapCut, Google Docs, basic Sheets, ChatGPT
- preferred work mode: writing, visual presentation, explaining
- customer interaction tolerance: medium
- camera tolerance: no; voice acceptable
- existing assets: university community access
- sales-model tolerance: service or repeatable product acceptable
- risk: low
- languages/market reach: Thai + workable English
- skill confidence: medium
- diagnostic mode: standard

Evidence trace:
- presentation/writing signal: classmates regularly ask for help fixing slides, summaries, and assignment formatting — confidence medium-to-high
- CapCut/Canva exposure alone is not treated as expert creative skill

## Persona 7 — Full-time worker with little available time

Normalized profile highlights:
- income goal: THB 5,000/month, optional-to-important
- revenue urgency: within 3 months
- available time: 45 minutes weekdays, 3 hours weekends; inconsistent during peak work weeks
- starting budget: low-to-moderate
- devices: Windows PC + Android + stable internet
- tool familiarity: Excel, Canva, ChatGPT, office software
- preferred work mode: organizing, writing, structured tasks
- customer interaction tolerance: low-to-medium
- camera tolerance: no
- existing assets: professional work experience
- sales-model tolerance: asynchronous service or slower-build asset acceptable
- risk: low
- speed vs scale: constrained primarily by time
- languages/market reach: Thai + working English
- skill confidence: medium
- diagnostic mode: standard

Evidence trace:
- document/presentation capability: colleagues ask for help making reports and presentations clearer — confidence medium
- limited time is retained as a hard constraint and not overwritten by income ambition

## Persona 8 — Unemployed with substantial available time

Normalized profile highlights:
- income goal: THB 10,000/month, urgent
- revenue urgency: within 7 days
- available time: 8 hours/day, consistent
- starting budget: very low, maximum loss THB 300
- devices: Windows laptop + Android + stable internet
- tool familiarity: Office, Facebook, basic ChatGPT
- preferred work mode: operations, researching, support, technology setup
- customer interaction tolerance: high
- camera tolerance: no; voice acceptable
- existing assets: previous customer-service/administrative experience
- sales-model tolerance: direct service acceptable
- risk: medium on effort, low on cash
- speed vs scale: strongly speed-first
- languages/market reach: Thai
- skill confidence: medium
- diagnostic mode: standard

Evidence trace:
- support/operations signal: previous work involved customer follow-up and administrative coordination — confidence medium-to-high
- technology signal: friends ask for basic device/app setup — confidence medium, not expert technical classification

## Persona 9 — Money available but little time

Normalized profile highlights:
- income goal: THB 20,000/month, optional
- revenue urgency: longer than 3 months acceptable
- available time: about 3 hours/week
- starting budget: flexible, maximum loss THB 20,000
- devices: Android + Windows + tablet + stable internet
- tool familiarity: office tools, ChatGPT; limited production-tool depth
- preferred work mode: planning, evaluating, delegating
- customer interaction tolerance: medium
- camera tolerance: no
- existing assets: capital, professional network, management experience
- distribution assets: network access but no established audience
- sales-model tolerance: building something slowly or investing to save time is acceptable
- risk: medium-to-high
- speed vs scale: scale can be prioritized over speed
- languages/market reach: Thai + English
- skill confidence: medium
- diagnostic mode: standard

Evidence trace:
- planning/coordination signal: has managed vendors and small projects professionally — confidence medium-to-high
- capital is recorded as an asset, not confused with execution skill

## Persona 10 — Almost no money, strong willingness to work

Normalized profile highlights:
- income goal: THB 6,000/month, urgent
- revenue urgency: within 7 days
- available time: 10 hours/day, consistent
- starting budget: zero
- maximum loss tolerance: effectively zero cash
- devices: Android phone + stable internet
- tool familiarity: Facebook, TikTok as user, basic ChatGPT
- preferred work mode: repetitive operations, follow-up, researching
- customer interaction tolerance: medium-to-high
- camera tolerance: no
- existing assets: time, high work capacity, basic prior operational experience
- sales-model tolerance: direct service acceptable
- risk: low cash risk, high effort tolerance
- speed vs scale: strongly speed-first
- languages/market reach: Thai
- skill confidence: medium-low
- diagnostic mode: standard with capability verification recommended

Evidence trace:
- operational reliability signal: previous work involved order follow-up and repetitive task completion; family members ask for help tracking deliveries and coordinating errands — confidence medium
- willingness to work is preserved separately and is not treated as proof of a professional skill

# Validation Gate Assessment

| P1 criterion | Result | Evidence |
| --- | --- | --- |
| All 10 personas can answer without business jargon | PASS | Questions rely on time, tools, behavior, comfort, assets, and constraints rather than niche/business terminology. |
| Profiles differ materially | PASS | Profiles diverge on urgency, time, budget, device capability, interaction tolerance, public presence, assets, work mode, risk, and market reach. |
| Unknown skills remain unknown | PASS | Persona 5 remains `skill_confidence = low` and `diagnostic_mode = skill_discovery`; no capability is invented. |
| Hard constraints are preserved | PASS | Examples include Persona 7's severe time limit, Persona 10's zero budget, Persona 8's 7-day urgency, Persona 3's low interaction tolerance, and Persona 5's Android-only setup. |
| Inferred capability is traceable | PASS | Every capability signal recorded above includes behavioral evidence and confidence. |
| No income recommendation is generated | PASS | Validation intentionally stops at normalized profiles. |
| Output is sufficient for P2 | PASS | P2 can match opportunity requirements against time, cost, devices, evidence-backed capability, sales/public tolerance, assets, urgency, risk, and reach. |

## Validation Conclusion

**P1 PASS**

The diagnostic produces meaningfully different profiles without forcing beginners to label their skills and without collapsing users into generic online-income advice.

The strongest result is the separation between:
- capability evidence and mere tool exposure
- cash budget and execution capability
- willingness to work and proven skill
- public-facing tolerance and actual work preference
- urgent income constraints and longer-term scale tolerance
- known capability and explicit skill-discovery mode

## Guardrails Carried Forward

P2 must not convert this PASS into false certainty.

P2 must preserve these rules:
- opportunity eligibility can eliminate options before ranking
- weak or unknown capabilities must reduce confidence rather than be invented
- an opportunity requiring a device, budget, sales behavior, public presence, or time commitment the user does not have must be penalized or excluded
- market-demand and opportunity metadata must come from a controlled Opportunity Library, not free-form LLM popularity guesses
- later real-user validation must track action and market response, not only whether users like the recommendation

## Handoff to P2

P1 is complete.

The next candidate phase is:

`P2 — Opportunity Library v0`

P2 should define a controlled set of income opportunities with metadata such as startup cost, time to first revenue, required capabilities, customer acquisition difficulty, margin, recurring-revenue potential, scalability, AI leverage, device requirements, public-presence requirements, and disqualifying constraints.

P2 must not begin until the owner explicitly approves progression beyond this P1 validation result.

## Product Principle

SoloForge should reduce wrong experiments, not merely produce more ideas.

The diagnostic exists so future recommendations can answer:

> Given this person's real constraints and evidence, what is the highest-probability income experiment to test first?

—not:

> What are some popular ways to make money online?
