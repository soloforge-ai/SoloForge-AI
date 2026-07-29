# 🚀 SoloForge AI

> **AI Creator Operating System for Affiliate Marketing**

SoloForge AI is an AI-powered platform that helps creators discover winning products, analyze affiliate opportunities, and generate high-quality content with minimal effort.

---

# ✨ Features

- 🛍 Product Catalog
- ⭐ MiniBoss Scoring Engine
- 📊 Featured Product Ranking
- 🤖 AI Content Generation
- 🎬 Content Studio
- 📱 Flutter Mobile App
- ⚡ JSON Pipeline
- 🔥 Affiliate Workflow

---

# 🏗 Architecture

```
CSV Product Feed
        │
        ▼
Feed Processor
        │
        ▼
MiniBoss Engine
        │
        ▼
JSON Catalog
        │
        ▼
Flutter App
        │
        ▼
AI Content Generation
```

---

# 📂 Project Structure

```
SoloForge-AI/
│
├── README.md
├── RUNBOOK.md
├── PROJECT_BIBLE.md
│
├── feed_processor/
│   ├── run.py
│   ├── sync_flutter.py
│   ├── test_miniboss.py
│   ├── miniboss.py
│   └── engine/
│
├── frontend/
│   ├── lib/
│   ├── assets/
│   └── pubspec.yaml
│
└── tools/
```

---

# 🚀 Quick Start

## Process Product Feed

```bash
cd feed_processor

python run.py
```

---

## Sync Flutter Data

```bash
python sync_flutter.py
```

---

## Run Flutter App

```bash
cd ../frontend

flutter pub get

flutter run
```

---

# 🧪 Testing

MiniBoss Regression Test

```bash
cd feed_processor

python test_miniboss.py
```

Expected

```
Full Result Equal
True
```

---

# 🛠 Tech Stack

### Backend

- Python
- JSONL
- MiniBoss Engine

### Mobile

- Flutter
- Dart

### Data

- JSON
- CSV

### AI

- Prompt Engineering
- Content Generation
- Affiliate Analysis

---

# 📈 Development Workflow

```
CSV
 ↓
run.py
 ↓
MiniBoss Engine
 ↓
ranked_products.jsonl
 ↓
sync_flutter.py
 ↓
catalog.json
 ↓
Flutter
 ↓
Generate Content
```

---

# 📚 Documentation

| Document | Description |
|----------|-------------|
| README.md | Project overview |
| RUNBOOK.md | Daily development commands |
| PROJECT_BIBLE.md | Complete project documentation |

---

# 🗺 Roadmap

### Sprint 31 ✅

- Modular MiniBoss Engine
- Production Migration
- Featured Catalog
- Flutter Sync
- Regression Testing

### Sprint 32

- Creator Engine
- Profit Score
- Trend Score
- Prompt Engine v2

### Future

- AI Video Pipeline
- Telegram Bot
- Auto Content Publishing
- Analytics Dashboard

---

# 🤝 Contributing

1. Create a new branch
2. Commit with Sprint number
3. Open Pull Request

Example

```
Sprint 32: Creator Engine
```

---

# 📄 License

Private Project

Copyright © SoloForge AI