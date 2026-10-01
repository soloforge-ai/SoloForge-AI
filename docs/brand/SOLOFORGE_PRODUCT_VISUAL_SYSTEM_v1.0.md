# SoloForge AI Product Visual System v1.0

**Status:** LOCKED BASELINE  
**Brand:** SoloForge AI  
**Visual Foundation:** ASH — AI Signature Hybrid  
**Applies to:** Apps, SaaS, bots, digital products, templates, reports, dashboards, creator tools, product pages, social assets, thumbnails, PDFs, and future SoloForge AI product families.

---

## 1. Purpose

This document defines the visual system for all SoloForge AI products.

The objective is not to make every product look identical. The objective is to make every product feel like it belongs to the same company.

SoloForge products must share a recognizable visual DNA while preserving enough differentiation for users to understand product type, hierarchy, and purpose.

### Core rule

**80% SoloForge Brand DNA + 20% Product Identity**

The shared 80% is controlled by:
- master palette
- typography behavior
- spacing
- component geometry
- visual hierarchy
- logo treatment
- imagery direction
- icon behavior
- lighting and materials
- surface treatment
- QA rules

The flexible 20% may vary by:
- product accent
- content imagery
- category motif
- product-specific illustration
- feature-specific visual cues

---

## 2. Source of Truth Hierarchy

When visual rules conflict, use this order:

1. `SoloForge AI Product Visual System v1.0`
2. `frontend/lib/core/theme/app_theme.dart`
3. `docs/visual/HUMAN_CRAFTED_VISUAL_DNA.md`
4. Approved SoloForge brand assets
5. Approved product-specific design
6. AI-generated suggestions

### Non-negotiable rule

**Existing approved SoloForge system beats a new AI-generated style suggestion.**

Do not create a new palette, visual language, or product identity unless the existing system cannot support the product.

---

## 3. Master Brand Palette — ASH

The current production palette is:

| Token | HEX | Role |
|---|---|---|
| Obsidian | `#0D0C0F` | Primary background |
| Black Plum | `#17131A` | Secondary background |
| Charcoal | `#1A161C` | Cards / elevated surfaces |
| Deep Indigo | `#28345C` | Primary hierarchy / trust / structure |
| Indigo Mist | `#596989` | Secondary UI / borders / support |
| Oxblood | `#541C2A` | Strong brand accent |
| Velvet Red | `#7A3042` | CTA / action / active state |
| Muted Rose | `#8A5963` | Soft emotional accent |
| Smoke Silver | `#A8ADB8` | Secondary text / metallic support |
| Bone White | `#E9E3DA` | Primary text / light surface |

### Default color ratio

Use approximately:

- 60–70% dark neutral surfaces
- 15–20% Indigo family
- 5–10% Oxblood / Velvet Red
- 5–10% Silver / Bone White / neutral highlights

Bright accent colors must never dominate the interface or product cover.

---

## 4. Color Behavior

### Backgrounds

Preferred:
- Obsidian
- Black Plum
- Charcoal

Avoid:
- pure white as the dominant SoloForge product background
- generic bright purple
- electric cyan
- rainbow gradients
- neon cyberpunk palettes

### Action colors

Primary CTA:
- Velvet Red

Secondary action:
- Deep Indigo

Premium / important emphasis:
- Oxblood

Support / inactive / border:
- Indigo Mist

### Text

Primary:
- Bone White

Secondary:
- Smoke Silver

Muted:
- Smoke Silver at reduced opacity

Never use low-contrast text over dark surfaces.

---

## 5. Product Family System

Each product inherits the ASH foundation and receives only a controlled product accent.

### 5.1 Core Platform / Creator OS

Examples:
- SoloForge AI App
- Creator OS
- MiniBoss
- Content Engine
- Approval Queue
- Product Discovery

**Accent:** Deep Indigo + Oxblood  
**Character:** intelligent, controlled, premium, technical  
**Visual motif:** system panels, modular grids, controlled data surfaces

### 5.2 Automation / Bot Products

Examples:
- Telegram bots
- workflow automations
- AI agents
- notification systems

**Accent:** Deep Indigo + Indigo Mist  
**Character:** operational, reliable, always-on  
**Visual motif:** connected nodes, flow paths, command surfaces, status indicators

Avoid literal robot imagery unless the product concept requires it.

### 5.3 Data / Analytics Products

Examples:
- dashboards
- data analysis kits
- Excel products
- reporting templates
- analytics services

**Accent:** Indigo Mist + Smoke Silver  
**Character:** analytical, precise, credible  
**Visual motif:** structured data, clean charts, grid logic, restrained metrics

Charts must prioritize readability over decorative styling.

### 5.4 Creator / AI Content Products

Examples:
- AI Character Consistency Kit
- Character Bible templates
- prompt systems
- Novel Creator Kit
- content workflow kits

**Accent:** Muted Rose + Velvet Red  
**Character:** creative, human, expressive, premium  
**Visual motif:** editorial layouts, character frames, image panels, controlled creative texture

### 5.5 Business / Strategy Products

Examples:
- business analysis
- founder analysis
- strategy kits
- planning systems
- business templates

**Accent:** Oxblood + Smoke Silver  
**Character:** executive, decisive, premium  
**Visual motif:** editorial business documents, structured frameworks, premium dark presentation

### 5.6 Experimental / Labs

Examples:
- experimental AI tools
- prototypes
- early-access systems
- R&D products

**Accent:** Deep Indigo with optional controlled secondary accent  
**Character:** exploratory but still credible  
**Visual motif:** prototype grids, system diagrams, controlled technical experimentation

Experimental does not mean visually chaotic.

---

## 6. Product Identity Rule

A product may have a secondary accent only if:

1. the ASH foundation remains dominant;
2. the accent helps users identify product purpose;
3. the accent does not conflict with existing SoloForge product families;
4. the accent is documented before production use.

A product may not invent a completely independent brand palette.

---

## 7. Logo System

### Required brand presence

Every public SoloForge product should include one of:

- SoloForge AI full wordmark
- approved SoloForge symbol mark
- approved watermark
- `by SoloForge AI` endorsement

### Hierarchy

For flagship products:
- SoloForge AI should be primary or co-primary.

For standalone product names:
- product name may lead;
- SoloForge endorsement must remain visible.

Example:

`PRODUCT NAME`  
`by SoloForge AI`

### Logo misuse

Do not:
- recolor the logo randomly
- distort proportions
- apply excessive glow
- place on busy backgrounds without contrast control
- generate substitute logos with AI
- change the symbol geometry per product

---

## 8. Typography System

Typography must feel:
- modern
- precise
- clean
- premium
- readable on mobile

Until a final font family is formally locked, use a clean sans-serif UI hierarchy and preserve consistent weight behavior.

### Hierarchy

**Display / Hero**
- strong but restrained
- short phrases
- high contrast
- avoid oversized decorative typography

**Heading**
- Medium / Semibold

**Body**
- Regular

**Caption / Metadata**
- Regular / Medium
- Smoke Silver

### Typography rule

Do not use more than two type families in a single product surface.

Do not use novelty fonts for core UI.

Important marketing text must be added in the design/layout layer, not generated inside AI images.

---

## 9. Geometry

### Corners

Default radius:
- cards: 14 px
- inputs: 12 px
- compact controls: 10–12 px
- badges: pill or 8–10 px depending on function

Avoid excessive rounded “toy-like” UI.

### Borders

Use:
- thin
- low contrast
- Indigo Mist or Smoke Silver at reduced opacity

Do not use thick glowing borders as a default.

### Shadows

Use subtle depth.

Preferred:
- restrained soft shadow
- dark elevation
- light material separation

Avoid:
- strong neon shadow
- heavy outer glow
- dramatic floating-card effects everywhere

---

## 10. Layout Language

SoloForge layouts must feel intentionally designed.

Preferred:
- strong grid
- clear hierarchy
- generous negative space
- modular cards
- disciplined alignment
- asymmetry when it improves composition

Avoid:
- visually crowded dashboards
- excessive decorative panels
- random floating elements
- too many competing focal points

### Visual hierarchy

Use:

1. Primary task / product promise
2. Main information
3. Supporting information
4. Metadata / secondary controls

One screen should have one dominant action.

---

## 11. Imagery — Human-Crafted Visual DNA

All generated imagery must inherit `HUMAN_CRAFTED_VISUAL_DNA.md`.

### Required qualities

- believable practical lighting
- realistic material behavior
- intentional composition
- natural depth
- restrained post-processing
- controlled texture
- clear focal hierarchy
- physically plausible shadows and reflections

### Avoid

- generic AI fantasy
- excessive bloom
- synthetic plastic surfaces
- perfect symmetry everywhere
- fake embedded copy
- random visual clutter
- generic purple cyberpunk
- over-detailed backgrounds

### Product imagery

When a real product reference exists, preserve its visual details.

Do not allow generation models to redesign real products.

---

## 12. Icons

Icons should be:

- simple
- geometric
- consistent stroke weight
- legible at small size
- primarily monochrome or ASH-tinted

Preferred colors:
- Bone White
- Smoke Silver
- Indigo Mist

Use accent colors only for state or hierarchy.

Do not mix unrelated icon families in the same product.

---

## 13. Charts and Data Visualization

Data visualization must prioritize interpretation.

### Default behavior

- dark canvas
- neutral grid
- Bone White primary labels
- Smoke Silver secondary labels
- Deep Indigo primary series
- Velvet Red / Oxblood for important comparison or alert
- additional series must remain muted

Do not assign bright colors to every series.

Do not sacrifice accuracy for aesthetics.

---

## 14. Product Cover System

Every digital product cover should contain:

1. Product name
2. Short product descriptor
3. Product-family visual cue
4. SoloForge AI endorsement
5. ASH base palette
6. controlled accent
7. strong whitespace / dark space

### Cover composition

Preferred:
- 1 dominant focal area
- 1 support visual
- 1 clear text zone

Avoid:
- dense feature lists on cover
- multiple CTA elements
- random icons
- excessive mockups

---

## 15. Digital Product Interior

PDFs, templates, checklists, guides, and workbooks should share:

### Header
- SoloForge / product identity
- section title

### Body
- clean content hierarchy
- high readability
- limited accent use

### Callout blocks
- Charcoal or Black Plum surface
- Deep Indigo or Oxblood edge/accent

### Footer
- product name or SoloForge AI
- optional version
- page number when appropriate

---

## 16. Product Page / Store Listing

Product listing visuals should follow this sequence:

1. **Hero** — what the product is
2. **Problem** — what pain it solves
3. **Outcome** — what improves after using it
4. **How it works**
5. **What's included**
6. **Who it is for**
7. **Example / proof / before-after**
8. **CTA**

All listing images should look like one visual campaign, not unrelated slides.

---

## 17. Social Product Content

Product promotion should inherit the same product-family accent.

Use consistent:
- background family
- typography
- corner radius
- logo position
- spacing
- CTA treatment

Do not change the visual identity for every post.

A campaign may vary imagery while preserving the system.

---

## 18. Motion / Video

Motion should feel:
- controlled
- deliberate
- premium
- functional

Preferred:
- subtle fade
- masked reveal
- short slide
- restrained parallax
- smooth status transitions

Avoid:
- excessive bounce
- random zoom
- constant glow
- unnecessary particle effects
- overuse of motion blur

---

## 19. Brand Watermark Rule

For content generated or exported by SoloForge AI:

Preferred:
- approved symbol mark
- `SoloForge AI`
- `Generated with SoloForge AI`
- `Powered by SoloForge AI`

Watermark must be:
- visible but not intrusive
- positioned consistently
- high contrast enough to remain legible

Default placements:
- bottom-right
- bottom-center for formal cover layouts

---

## 20. Product Family Accent Matrix

| Product Family | Primary Base | Main Accent | Support Accent |
|---|---|---|---|
| Core Platform | Obsidian | Deep Indigo | Oxblood |
| Automation / Bots | Obsidian | Deep Indigo | Indigo Mist |
| Data / Analytics | Obsidian | Indigo Mist | Smoke Silver |
| Creator / Content | Black Plum | Muted Rose | Velvet Red |
| Business / Strategy | Obsidian | Oxblood | Smoke Silver |
| Labs / Experimental | Obsidian | Deep Indigo | controlled product accent |

---

## 21. 80/20 Consistency Test

Before approving a new product design, ask:

### 80% Brand DNA

- Does it clearly feel like SoloForge AI?
- Does it use the ASH foundation?
- Is typography behavior consistent?
- Are spacing and geometry consistent?
- Does the logo follow the same rules?
- Does the imagery follow Human-Crafted Visual DNA?
- Does the product maintain dark-luxury restraint?

### 20% Product Identity

- Can users distinguish the product family?
- Is the accent purposeful?
- Is the product-specific motif useful?
- Does differentiation improve comprehension?

If the design fails the 80% section, it is not ready.

---

## 22. New Product Creation Workflow

```text
Product Idea
    ↓
Assign Product Family
    ↓
Apply ASH Foundation
    ↓
Select Approved Family Accent
    ↓
Apply SoloForge Layout System
    ↓
Create Product-Specific Visual Cue
    ↓
Apply Human-Crafted Visual DNA
    ↓
Brand QA
    ↓
Product QA
    ↓
Approve
    ↓
Register as Reusable Asset
```

Do not begin a new product by choosing random colors or browsing arbitrary design inspiration.

---

## 23. AI Agent Instruction

When an AI system generates SoloForge product visuals:

```text
You are producing an official SoloForge AI product asset.

Always inherit the SoloForge AI Product Visual System.

Base palette:
Obsidian #0D0C0F
Black Plum #17131A
Charcoal #1A161C
Deep Indigo #28345C
Indigo Mist #596989
Oxblood #541C2A
Velvet Red #7A3042
Muted Rose #8A5963
Smoke Silver #A8ADB8
Bone White #E9E3DA

Use dark-luxury restraint.
Do not invent a new brand palette.
Use product-family accent only as a controlled secondary identity.
Preserve clear hierarchy, negative space, and human-crafted visual realism.
Do not generate important marketing copy inside the image.
Do not redesign the SoloForge logo.
```

---

## 24. QA Checklist

A product visual is approved only if all critical checks pass.

### Brand

- [ ] ASH foundation is visible
- [ ] No unauthorized palette
- [ ] Logo treatment is correct
- [ ] Product-family accent is correct
- [ ] Dark-luxury restraint is preserved

### Layout

- [ ] clear visual hierarchy
- [ ] spacing is consistent
- [ ] no overcrowding
- [ ] one primary focal point
- [ ] mobile readability is acceptable

### Typography

- [ ] important text is readable
- [ ] typography is consistent
- [ ] no AI-generated text artifacts
- [ ] no unnecessary font mixing

### Imagery

- [ ] human-crafted realism
- [ ] plausible lighting
- [ ] plausible materials
- [ ] no generic AI look
- [ ] product/character identity preserved

### Product

- [ ] product family is recognizable
- [ ] accent supports function
- [ ] visual does not conflict with another product
- [ ] product can scale across store, app, PDF, and social assets

If a critical item fails:

`STATUS = NEEDS REVISION`

If all pass:

`STATUS = PRODUCT VISUAL APPROVED`

---

## 25. Governance

This document is the product-level visual governance layer for SoloForge AI.

### Changes requiring version update

- master palette changes
- logo system changes
- product-family taxonomy changes
- typography lock
- major component geometry changes
- new global visual language

### Minor additions

New product-family examples or approved motifs may be added without redesigning the whole system.

---

## 26. Implementation Targets

This visual system should eventually map into reusable machine-readable and code assets:

```text
docs/brand/
├── SOLOFORGE_PRODUCT_VISUAL_SYSTEM_v1.0.md
├── COLOR_TOKENS.md
├── TYPOGRAPHY.md
├── PRODUCT_FAMILIES.md
└── COMPONENT_RULES.md

frontend/lib/core/design_system/
├── colors.dart
├── typography.dart
├── spacing.dart
├── radius.dart
├── shadows.dart
└── theme.dart
```

Existing production colors currently live in:

`frontend/lib/core/theme/app_theme.dart`

Until migration is intentionally performed, that file remains the runtime color source.

---

## 27. Final Principle

**Consistency before novelty.**

SoloForge AI should become recognizable even when the logo is small.

A new product may feel different.

It must never feel unrelated.
