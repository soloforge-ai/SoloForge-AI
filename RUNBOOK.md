# 🚀 SoloForge AI - RUNBOOK

> Daily Development Guide
>
> Last Updated: Sprint 31

---

# 📋 Purpose

This document contains all commands, workflows, and troubleshooting steps required for daily development.

If you don't remember how to run the project, start here.

---

# 📁 Project Structure

```
SoloForge-AI/
│
├── README.md
├── RUNBOOK.md
├── PROJECT_BIBLE.md
│
├── feed_processor/
│
├── frontend/
│
└── tools/
```

---

# 🚀 Daily Workflow

```
CSV Feed
     │
     ▼
run.py
     │
     ▼
MiniBoss Engine
     │
     ▼
ranked_products_xxxx.jsonl
     │
     ▼
sync_flutter.py
     │
     ▼
catalog.json
featured_catalog.json
     │
     ▼
Flutter App
     │
     ▼
Generate Content
```

---

# 1️⃣ Process Product Feed

ใช้เมื่อข้อมูลสินค้ามีการเปลี่ยนแปลง

```bash
cd feed_processor

python run.py
```

Expected

```
Processing Complete
Products : 1,000,000
Chunks : 20
```

Output

```
data/processed/

ranked_products_0001.jsonl
...
ranked_products_0020.jsonl
```

---

# 2️⃣ Sync Flutter

หลังจาก run.py เสร็จทุกครั้ง

```bash
python sync_flutter.py
```

Output

```
frontend/assets/data/catalog.json

frontend/assets/data/featured_catalog.json
```

Expected

```
Flutter Sync Complete

Catalog Products : 1000

Featured : 200
```

---

# 3️⃣ Run Flutter

```
cd ../frontend

flutter pub get

flutter run
```

---

# 4️⃣ Flutter Only

เมื่อแก้เฉพาะ UI

```bash
flutter run
```

---

# 5️⃣ Hot Reload

Flutter

```
r
```

Hot Restart

```
R
```

Quit

```
q
```

---

# 6️⃣ Test MiniBoss

Regression Test

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

# 7️⃣ Git Workflow

Check Status

```bash
git status
```

Add

```bash
git add .
```

Commit

```bash
git commit -m "Sprint XX: Description"
```

Push

```bash
git push origin main
```

---

# 8️⃣ Flutter Clean

```bash
flutter clean

flutter pub get
```

---

# 9️⃣ Python Cache

Delete

```
__pycache__/
```

---

# 🔟 Scanner

```bash
cd tools/scanner

python scanner.py
```

Output

```
PROJECT_MAP.md

PROJECT_TREE.md

PROJECT_STATUS.md

PROJECT_STATS.md

PROJECT_INTELLIGENCE.md
```

---

# 📂 Important Files

## Product Processing

```
feed_processor/run.py
```

---

## MiniBoss

```
feed_processor/miniboss.py
```

---

## Flutter Sync

```
feed_processor/sync_flutter.py
```

---

## Regression Test

```
feed_processor/test_miniboss.py
```

---

## Home Page

```
frontend/lib/pages/home_page.dart
```

---

## Catalog

```
frontend/assets/data/catalog.json
```

---

## Featured Catalog

```
frontend/assets/data/featured_catalog.json
```

---

# 🧪 Verification Checklist

หลังจากแก้ไข MiniBoss

- [ ] test_miniboss.py ผ่าน
- [ ] run.py ผ่าน
- [ ] sync_flutter.py ผ่าน
- [ ] flutter run ผ่าน
- [ ] Home Page แสดงสินค้า
- [ ] Featured Products แสดง
- [ ] Product Detail เปิดได้
- [ ] ไม่มี Error ใน Console

---

# 🐞 Common Problems

## GitHub Push Failed

```
File is larger than 100 MB
```

Solution

- Remove large files from Git
- Ignore generated JSONL files
- Commit again

---

## Flutter Asset Not Found

Run

```bash
flutter clean

flutter pub get

flutter run
```

---

## MiniBoss Result Changed

Run

```bash
python test_miniboss.py
```

Expected

```
Full Result Equal

True
```

---

# 🚀 Release Checklist

Before Commit

- [ ] git status
- [ ] test_miniboss.py
- [ ] flutter run
- [ ] No Console Errors
- [ ] README Updated
- [ ] RUNBOOK Updated

---

# 📅 Sprint History

Sprint 29-30

- AI Forge MVP
- Prompt Engine Foundation

Sprint 31

- Modular MiniBoss Engine
- Production Migration
- Regression Testing
- Flutter Sync
- Featured Catalog

---

# 🎯 Current Architecture

```
CSV

 │

 ▼

Transformer

 │

 ▼

MiniBoss Engine

 │

 ▼

JSONL

 │

 ▼

Sync Flutter

 │

 ▼

Catalog

 │

 ▼

Flutter

 │

 ▼

Generate Content
```

---

# 📝 Notes

Always execute the pipeline in this order:

```
python run.py

↓

python sync_flutter.py

↓

flutter run
```

Do not edit generated JSON files manually.

Generated files:

- catalog.json
- featured_catalog.json
- ranked_products_*.jsonl


# Developer Shortcuts

📌 แก้ UI อย่างเดียว
→ flutter run

📌 ข้อมูลสินค้าเปลี่ยน
→ run.py
→ sync_flutter.py
→ flutter run

📌 แก้ MiniBoss
→ test_miniboss.py
→ run.py
→ sync_flutter.py
→ flutter run

📌 ก่อน Commit
→ git status
→ flutter run
→ test_miniboss.py
→ git commit