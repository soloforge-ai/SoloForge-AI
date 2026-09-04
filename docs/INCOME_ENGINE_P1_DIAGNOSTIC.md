# SoloForge Income Engine — P1 Income Diagnostic v0

Status: Validation Spec

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

## Handoff to P2

Only after P1 passes validation should SoloForge create P2:

`Opportunity Library v0`

P2 will define a controlled set of income opportunities with metadata such as startup cost, time to first revenue, required capabilities, customer acquisition difficulty, margin, recurring-revenue potential, scalability, and AI leverage.

P1 does not choose among those opportunities.

## Product Principle

SoloForge should reduce wrong experiments, not merely produce more ideas.

The diagnostic exists so future recommendations can answer:

> Given this person's real constraints and evidence, what is the highest-probability income experiment to test first?

—not:

> What are some popular ways to make money online?
