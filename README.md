# 🚀 SoloForge AI

> **AI Creator Operating System**

SoloForge AI is a modular AI-powered platform for creators, affiliate marketers, and solo entrepreneurs.

The project combines product intelligence, content generation, creative production, publishing, and automation into a reusable creator operating system.

---

# 🎯 Current Product Direction

## SoloForge State Reset — Content Factory E2E Proof

The active goal is not to add more features.

The active goal is to prove that the systems already implemented can complete one real production workflow from idea to published post:

```text
Idea
→ Analyze / MiniBoss
→ AI Generate
→ Review
→ Approve
→ Asset Generation
→ SoloForge Branding
→ TTS / Final Render when required
→ Ready to Publish
→ Publora
→ Real Published Post
```

After this path is proven end-to-end, the next approved business initiative is:

```text
Idea #003
Audience / Pain
→ Content
→ Lead Magnet
→ Lead Capture
→ Validation
→ Offer
→ Pre-sell
→ Build
→ Deliver
```

Core business rule:

> **Don't build inventory. Build validated offers.**

---

# ✅ Production / Retained Foundations

The following foundations are implemented and retained on `main`:

- Flutter mobile application
- Product Catalog and discovery
- Feed Processor
- MiniBoss scoring and ranking
- Product Intelligence / Product Forge foundations
- Content Job workflow
- Idea analysis and content-format recommendations
- AI text-generation infrastructure
- Asset generation
- SoloForge AI branding on generated visual output
- TTS pipeline
- Subtitle and final-render pipeline
- Supabase-backed content state / storage integration
- Publora publishing integration
- Content analytics / performance ingestion foundations
- Telegram-related retained workflows
- Asset Forge v1
- Pollinations OAuth/session infrastructure
- Character Memory bridge used by Asset Forge
- Project Scanner / project-intelligence tooling
- Android APK CI build
- Render production smoke checks

Implemented does not automatically mean the complete commercial workflow has been proven end-to-end in production.

---

# 🚧 Current Gate

Before expanding the product, SoloForge must complete these steps in order:

1. **Update Source of Truth** so repository documentation reflects the real implementation state.
2. **PR Cleanup** — classify open work as Merge / Close / Archive / Keep.
3. **Content Factory E2E Proof** — run one real idea through:
   `Idea → Generate → Approve → Asset → Publish`.
4. **Idea #003 Validation Loop** — add lead capture, demand validation, offer testing, and pre-sell only after the E2E content path is green.

Definition of Done for the current product gate:

> One real content job begins as an idea inside SoloForge and reaches a real published destination with traceable evidence across the workflow.

---

# 🟡 Implemented but Not Yet Fully Proven as One Production Loop

These capabilities exist in code but must not be described as fully production-proven until the current E2E gate is completed:

- live AI provider execution for the current content workflow
- autonomous asset/video progression across every required worker
- real Publora-to-platform publishing from the same tested content job
- post-publication performance feedback closing the loop
- unattended 24/7 content operation

---

# ❄️ Frozen / Not Active Roadmap Drivers

Do not expand these unless the owner explicitly re-authorizes them:

- Chat Prawtwan expansion
- Idea Flow / Telegram Idea Inbox expansion
- SoloForge Income Engine P2+
- new agent systems
- new memory systems
- billing
- unrelated business verticals
- broad architecture refactors

Existing retained implementations may remain in the repository without being active roadmap priorities.

---

# ✨ Core Capabilities

- 🛍 Product Intelligence Engine
- ⭐ MiniBoss Scoring Engine
- 📊 Affiliate Product Analysis
- 🤖 AI Content Generation
- 🎬 Content Studio / Content Jobs
- 🖼 Asset Generation and Branding
- 🔊 TTS and Final Render
- 📤 Publora Publishing Integration
- 📈 Analytics / Performance Foundations
- 📱 Flutter Mobile Application
- ⚡ Documentation Pipeline
- 🧠 Project Intelligence
- 🚀 Developer Launcher

---

# 🏗 High-Level Architecture

```text
Idea / Product
      │
      ▼
Analysis / MiniBoss
      │
      ▼
Content Job
      │
      ▼
AI Generation
      │
      ▼
Review / Approval
      │
      ▼
Asset / Audio / Render
      │
      ▼
Ready to Publish
      │
      ▼
Publora
      │
      ▼
Published Platform
```

The architecture already contains many of these components. The current milestone is to verify that they operate correctly as one continuous production path.

---

# 📂 Project Structure

```text
SoloForge-AI/
│
├── .ai/                # AI Development Protocol and project context
├── backend/
├── data/
├── docs/
├── feed_processor/
├── frontend/
├── portfolio/
├── rules/
├── supabase/
├── tools/
│
├── README.md
├── RUNBOOK.md
├── render.yaml
└── dev.py
```

---

# 🚀 Quick Start

## Developer Launcher

```bash
py dev.py
```

## Flutter

```bash
cd frontend
flutter pub get
flutter run
```

## Product Pipeline

```bash
cd feed_processor
python run.py
```

---

# 🧪 Verification

Current automated verification includes:

- Android APK build workflow
- Asset Forge backend tests
- Asset Forge production smoke checks
- MiniBoss / feed-processing tests
- targeted backend contract tests

These checks validate important components, but they do **not** replace the current Content Factory E2E proof.

---

# 🛠 Technology Stack

## Frontend

- Flutter
- Dart

## Backend

- Python
- FastAPI

## Persistence / Storage

- Supabase
- local persistence where appropriate
- Firebase retained where applicable

## AI / Generation

- Pollinations
- Gemini-compatible qualification / generation paths
- Groq-compatible generation path
- OpenRouter-compatible generation path
- provider abstraction and qualification tooling

## Media

- Pillow
- Edge TTS
- FFmpeg

## Publishing

- Publora

## Development

- Git
- GitHub
- GitHub Actions
- Render
- VS Code

---

# 📚 Documentation Authority

Current project intent must be read in this order:

1. Explicit owner instruction
2. `docs/CURRENT_SPRINT.md`
3. `docs/ROADMAP.md`
4. `.ai/AI_CONTEXT.md`
5. `.ai/AI_TASK.md`
6. Project Scanner output

Project Scanner describes observed implementation. It must not replace human-approved product intent.

---

# 🤖 AI Development Protocol

AI assistants should read:

1. `.ai/PROTOCOL.md`
2. `.ai/AI_CONTEXT.md`
3. `.ai/AI_RULES.md`
4. `.ai/AI_TASK.md`
5. `docs/CURRENT_SPRINT.md`

The active instruction for this cycle is:

> Do not add unrelated features. Fix only what is required to establish the real Content Factory E2E path.

---

# 📄 Project Status

**Status:** Active Development  
**Active Initiative:** SoloForge State Reset  
**Current Milestone:** Content Factory E2E Proof  
**Source-of-Truth Date:** 2026-10-01

---

Copyright © SoloForge AI
