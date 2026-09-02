from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .db import DEFAULT_DB_PATH
from .service import IdeaFlowService

HELP = """SoloForge Idea Flow

ส่งข้อความธรรมดา = capture ไอเดีย

/list [STATUS]
/view ID
/search TEXT
/research ID TEXT
/score ID DEMAND FEASIBILITY STRATEGIC_FIT [NOTE]
/graduate ID [reason]
/park ID [reason]
/reject ID [reason]
/experiment ID [reason]
/validate ID [reason]
/kill ID [reason]
/history ID
/help
"""


def request(token: str, method: str, params: dict[str, object]) -> object:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=70) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return payload["result"]


def send(token: str, chat_id: int, text: str) -> None:
    request(token, "sendMessage", {"chat_id": chat_id, "text": text[:4000]})


def format_list(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "ไม่มีไอเดียในรายการนี้"
    return "\n".join(f"#{r['id']} [{r['status']}] {r['title']}" for r in rows)


def handle_text(service: IdeaFlowService, text: str, *, actor: str) -> str:
    text = (text or "").strip()
    if not text:
        return "ข้อความว่าง"
    if not text.startswith("/"):
        idea_id = service.capture(text, source="telegram", actor=actor)
        return f"จับไว้แล้ว ✅ Idea #{idea_id}\nสถานะ: CAPTURED"

    parts = text.split()
    cmd = parts[0].split("@")[0].lower()
    if cmd in {"/help", "/start"}:
        return HELP
    if cmd == "/list":
        status = parts[1].upper() if len(parts) > 1 else None
        return format_list(service.list(status=status))
    if cmd == "/search":
        return format_list(service.search(" ".join(parts[1:])))
    if cmd == "/view":
        row = service.get(int(parts[1]))
        ev = row["latest_evaluation"]
        extra = ""
        if ev:
            extra = f"\nScore: {ev['weighted_score']}/5\nSignal: {ev['signal']}"
        return f"#{row['id']} [{row['status']}]\n{row['body']}{extra}"
    if cmd == "/history":
        events = service.history(int(parts[1]))
        return "\n".join(
            f"{e['created_at']} | {e['event_type']} | {e['from_status'] or '-'} -> {e['to_status'] or '-'}"
            for e in events[-20:]
        )
    if cmd == "/research":
        idea_id = int(parts[1])
        service.mark_researched(idea_id, " ".join(parts[2:]), actor=actor)
        return f"#{idea_id} -> RESEARCHED ✅"
    if cmd == "/score":
        if len(parts) < 5:
            return "ใช้: /score ID DEMAND FEASIBILITY STRATEGIC_FIT [NOTE]"
        idea_id = int(parts[1])
        result = service.evaluate(
            idea_id,
            demand=int(parts[2]),
            feasibility=int(parts[3]),
            strategic_fit=int(parts[4]),
            notes=" ".join(parts[5:]),
            evaluator=actor,
        )
        return f"#{idea_id} EVALUATED ✅\nScore: {result['weighted_score']}/5\nSignal: {result['signal']}"

    transitions = {
        "/triage": "TRIAGED",
        "/graduate": "GRADUATED",
        "/park": "PARKED",
        "/reject": "REJECTED",
        "/experiment": "EXPERIMENT",
        "/validate": "VALIDATED",
        "/kill": "KILLED",
    }
    if cmd in transitions:
        idea_id = int(parts[1])
        target = transitions[cmd]
        service.transition(idea_id, target, actor=actor, reason=" ".join(parts[2:]))
        return f"#{idea_id} -> {target} ✅"

    return "ไม่รู้จักคำสั่ง\n\n" + HELP


def run(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed_chat_id = os.environ.get("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")
    if not allowed_chat_id:
        raise SystemExit("TELEGRAM_ALLOWED_CHAT_ID is required")

    offset: int | None = None
    with IdeaFlowService(db_path) as service:
        print("SoloForge Idea Flow Telegram bot running. Ctrl+C to stop.")
        while True:
            try:
                params: dict[str, object] = {"timeout": 50}
                if offset is not None:
                    params["offset"] = offset
                updates = request(token, "getUpdates", params)
                for update in updates:  # type: ignore[union-attr]
                    offset = update["update_id"] + 1
                    message = update.get("message") or {}
                    text = message.get("text")
                    chat_id = (message.get("chat") or {}).get("id")
                    if not text or chat_id is None:
                        continue
                    if str(chat_id) != allowed_chat_id:
                        send(token, chat_id, "Bot นี้เป็น private SoloForge idea inbox")
                        continue
                    actor = f"telegram:{chat_id}"
                    try:
                        reply = handle_text(service, text, actor=actor)
                    except Exception as exc:
                        reply = f"Error: {exc}"
                    send(token, chat_id, reply)
            except KeyboardInterrupt:
                return
            except Exception as exc:
                print(f"Telegram error: {exc}")
                time.sleep(3)


if __name__ == "__main__":
    run()
