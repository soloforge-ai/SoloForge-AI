# SoloForge Idea Flow

Internal Founder OS tool for capturing "ไอเดียฟุ้ง" before they accidentally become projects.

## Design goal

Idea Flow is deliberately separated from Asset Forge and other user-facing SoloForge product code.
Its job is to create friction **before execution**, not to automate execution.

```text
CAPTURED
  -> TRIAGED
  -> RESEARCHED (optional)
  -> EVALUATED
  -> GRADUATED -> EXPERIMENT -> VALIDATED / KILLED
       |              |
       +-> PARKED <---+

Any early-stage idea may also be PARKED or REJECTED where allowed by the state machine.
```

`GRADUATED` means "worth spending resources on an experiment". It does **not** mean "build a full product".

## Source of truth

Local SQLite database:

```text
data/runtime/idea_flow.db
```

`data/runtime/` is intentionally ignored by Git. Runtime ideas must not be committed.

SQLite settings:

- foreign keys enabled
- WAL mode
- busy timeout
- migration checksum tracking
- database trigger for invalid status transitions
- UTC timestamps

## Scoring

Three axes, each 0-5:

- Market Demand: 45%
- Feasibility: 20%
- Strategic Fit / Leverage: 35%

The score is only a decision aid. `GRADUATED`, `PARKED`, and `REJECTED` remain explicit human decisions.

## CLI

Run from the SoloForge repository root:

```powershell
python -m tools.idea_flow.cli capture "ทำระบบคัด quote จากนิยาย"
python -m tools.idea_flow.cli list
python -m tools.idea_flow.cli search quote
python -m tools.idea_flow.cli research 1 "มี pain จริง: ต้องค้น manuscript ทีละบท"
python -m tools.idea_flow.cli score 1 5 5 5 --notes "ใช้ workflow และ assets เดิมได้"
python -m tools.idea_flow.cli graduate 1 --reason "ผ่านเกณฑ์ ทำ experiment เล็ก"
python -m tools.idea_flow.cli experiment 1
python -m tools.idea_flow.cli validate 1 --reason "ใช้จริงต่อเนื่อง"
python -m tools.idea_flow.cli history 1
```

## Telegram private inbox

Create a bot with `@BotFather`, then in PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_ALLOWED_CHAT_ID="..."   # strongly recommended
python -m tools.idea_flow.telegram
```

Plain messages are captured immediately. Commands support list, search, research, scoring and lifecycle decisions.

## Security

Do not commit bot tokens. Environment variables only.
Use `TELEGRAM_ALLOWED_CHAT_ID` so the bot behaves as a private inbox.

## Intentionally excluded from V0

- LLM calls
- web research agents
- autonomous decisions
- repo creation
- automatic coding
- auto-deploy
- vector database

Those should only be added after the capture/review workflow proves useful in real daily use.

## Tests

```powershell
python -m unittest tools.idea_flow.tests.test_idea_flow -v
```
