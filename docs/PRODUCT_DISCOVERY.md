# 🚀 Product Discovery Engine

> Sprint 43 Specification

---

# Overview

Product Discovery Engine is the core system responsible for selecting the best products for content creation.

Unlike previous versions, the engine **does not require an Affiliate Link** before a product can be ranked.

The goal is to discover products with the highest content potential from the entire product database.

---

# Objectives

- Discover the best products from all imported products.
- Rank products within each category.
- Build a Content Queue for creators.
- Remove Affiliate Link as a required condition.
- Support future AI Content Generation.

---

# Current Problem

Current workflow

```
Shopee Product Feed
        │
        ▼
Merge Affiliate Catalog
        │
        ▼
MiniBoss
        │
        ▼
Flutter
```

Problems

- Only products with Affiliate Links are available.
- Product selection is heavily limited.
- Many high-potential products are ignored.
- Manual Affiliate collection becomes a bottleneck.

---

# New Workflow

```
Raw Product Feed
        │
        ▼
Normalize
        │
        ▼
MiniBoss Engine
        │
        ▼
Category Ranking
        │
        ▼
Content Discovery
        │
        ▼
Top Products
        │
        ▼
Affiliate Enrichment (Optional)
        │
        ▼
Content Pipeline
```

---

# Discovery Pipeline

Stage 1

Import Product Feed

↓

Normalize Product Data

↓

Calculate MiniBoss Score

↓

Assign Category

↓

Rank Products

↓

Export Category Lists

---

Stage 2

Creator selects product

↓

Open Product Page

↓

Generate / Copy Affiliate Link

↓

Update Product

---

Stage 3

Generate Content

↓

Storyboard

↓

Image

↓

Video

↓

Subtitle

↓

Publish

---

# Product States

Every product has one workflow state.

```
Imported

↓

Ranked

↓

Content Ready

↓

Affiliate Ready

↓

Published
```

---

# Product Categories

Products are grouped by category.

Example

- Beauty
- Mobile
- Home
- Kitchen
- Pet
- Fashion
- Sports
- Stationery
- Automotive
- Electronics

Future versions may normalize Shopee categories into SoloForge categories.

---

# Ranking

Products are ranked inside each category.

Example

```
Beauty

Top 1

Top 2

...

Top 100
```

---

# Discovery Filters

Current filters

- MiniBoss Score
- Rating
- Sold
- Discount
- Shop Rating
- Official Shop
- Preferred Shop
- Stock

Future filters

- Content Score
- Viral Potential
- Seasonal Score
- Trend Score

---

# Output

Example

```
output/

Beauty.json

Mobile.json

Kitchen.json

Pet.json

Fashion.json
```

or

```
catalog_by_category.json
```

---

# Affiliate Policy

Affiliate Link is optional.

Products without Affiliate Links are still ranked.

Affiliate information is added only after the creator decides to produce content.

---

# Future Content Score

Future versions will calculate

- Content Potential
- Hook Potential
- Demo Potential
- Before / After Potential
- Problem Solving Potential

This score is independent from MiniBoss.

---

# Sprint 43 Scope

Included

- Product Discovery
- Category Ranking
- Category Export
- Workflow redesign

Excluded

- AI Prompt Generation
- Storyboard Generation
- Video Generation
- Auto Publishing
- Trend Prediction

---

# Success Criteria

Sprint 43 is complete when the system can

- Read all products
- Rank products by category
- Export Top Products
- Ignore missing Affiliate Links
- Prepare products for future content creation

---

# Long-term Vision

```
1,000,000 Products

↓

Product Discovery Engine

↓

Top Products

↓

Content Discovery

↓

Content Production

↓

Affiliate Enrichment

↓

Publish

↓

Revenue
```

The Product Discovery Engine is the foundation of the SoloForge AI Creator Operating System.