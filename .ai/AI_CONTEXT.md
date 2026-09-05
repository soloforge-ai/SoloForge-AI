# Reading Time

Estimated Reading Time

30 seconds

Purpose

Project Snapshot

Read Before

AI_RULES.md

AI_TASK.md

PROTOCOL.md

# SoloForge AI Context

Version: v1.3.0

---

# Project Overview

Project Name

SoloForge AI

Project Type

AI Creator Operating System

Mission

Build a commercial-grade AI platform that enables creators, affiliate marketers, and solo entrepreneurs to turn product data into useful business content and digital outputs with AI-assisted workflows.

---

# Current Development Status

Status

Active Development

Current Objective

SoloForge Product-to-Post — Cleanup Scope Reset #1.

The owner has reset the active product direction to the original commercial workflow:

```text
Product
→ Extract / load product data
→ Evaluate product opportunity
→ Select selling angle
→ Generate creative + caption
→ Review
→ Export ready-to-post package
```

The immediate objective is to reduce scope drift, preserve reusable components, and then prove one real Product-to-Post workflow before expanding architecture.

Asset Forge v1 remains Working Product #1 and a reusable creative/image-processing component. It should not be reopened for non-blocking polish by default.

---

# Technology Stack

Frontend

- Flutter

Backend

- Python

Database / Persistence

- Firebase
- Supabase
- Local persistence where appropriate for internal tools

Version Control

- Git
- GitHub

Documentation

- Markdown

Development Tools

- Flutter
- Python
- VS Code

AI Tools

Current

- ChatGPT
- CapCut AI
- Pollinations

Planned / Optional

- Claude
- Gemini
- Perplexity

---

# Project Structure

Core directories

frontend/
backend/
assets/
data/
docs/
feed_processor/
tools/
prompts/
rules/
.ai/

Purpose

docs/

Human documentation.

.ai/

AI protocol and context.

tools/

Developer tools and automation.

assets/

Application assets.

data/

Application data.

---

# Architecture

Development follows a modular architecture.

Preferred structure

Presentation

↓

Services

↓

Models

↓

Data

↓

External Services

Business logic should remain separated from UI whenever possible.

---

# Active Product Foundations

- Product Feed / Feed Processor
- Product Catalog and category data
- MiniBoss scoring and ranking
- Product Intelligence
- Product Forge / Content Studio
- Content Engine and prompt infrastructure
- Flutter frontend foundation

---

# Retained Components

- Asset Forge v1 — Working Product #1 and reusable creative/image-processing component
- Pollinations OAuth/session infrastructure used by Asset Forge
- Asset Forge Character Memory bridge currently wired into runtime
- Asset Forge output-quality processing
- SoloForge AI Development Protocol v1.0

Do not remove retained shared infrastructure when an active component still depends on it.

---

# Frozen Capabilities / Initiatives

The following remain merged or documented but are not active roadmap drivers:

- Chat Prawtwan MVP
- Idea Flow / Supabase-backed Telegram Idea Inbox
- SoloForge Income Engine P1

Income Engine P1 remains valid historical work. `P2 — Opportunity Library v0` is frozen and must not begin unless explicitly re-authorized by the owner.

---

# Development Philosophy

Prioritize

Useful business output

↓

Correctness

↓

Consistency

↓

Maintainability

↓

Scalability

Prefer simple workflow completion over architecture expansion.

---

# Documentation Structure

Human Documentation

/docs

AI Documentation

/.ai

Generated documentation should remain synchronized with the project.

Generated project intelligence must not overwrite human sprint state.

---

# Engineering Standards

Primary Language

English

Documentation

Markdown

Architecture

Modular

Coding Style

Readable

Maintainable

Scalable

---

# Important Constraints

Always preserve project architecture.

Avoid unrelated modifications.

Do not rename existing folders without approval.

Do not rewrite completed systems unless requested.

Keep documentation synchronized with implementation.

Do not treat generated scanner output as authoritative human sprint state.

Do not expand frozen initiatives without explicit owner approval.

---

# Current Focus

The active focus is Product-to-Post.

The governing product question is:

> Can one real product enter SoloForge and leave as a useful, reviewable, ready-to-post package?

For the current cleanup:

- remove dead/legacy frontend implementations that have no production caller
- remove Chat Prawtwan and Developer Tools entry points from Home
- preserve Product Catalog, MiniBoss, Product Intelligence, Product Forge, Content Engine, and Asset Forge
- preserve shared runtime dependencies required by retained components
- do not modify backend Prawtwan or Idea Flow routes in Cleanup #1

After cleanup, identify the smallest missing Product Forge gaps needed for one real end-to-end run.

Do not automatically add billing, general authentication, autonomous posting, new agents, advanced memory, video/audio, or unrelated verticals merely because they remain possible future work.

---

# AI Responsibilities

Every AI assistant should

- understand project context
- follow AI_RULES.md
- follow PROTOCOL.md
- follow AI_TASK.md
- preserve architecture
- minimize unnecessary changes
- explain important technical decisions
- prefer current ACTIVE Product-to-Post decisions over superseded context
- treat Asset Forge as a retained component unless a blocker or explicit owner priority requires reopening it
- avoid expanding frozen initiatives without explicit approval

---

# Future Direction

SoloForge may eventually coordinate multiple AI tools and specialized workflows, but future expansion must be justified by concrete product or business value.

The near-term priority is not to become a broader platform. It is to complete and validate the Product-to-Post business loop first.

---

End of Context
