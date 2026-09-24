"""Private Telegram webhook backed by Supabase Idea Flow RPCs."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/telegram/idea-inbox", tags=["idea-inbox"])

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


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _supabase_request(
    method: str,
    path: str,
    *,
    body: dict[str, object] | None = None,
    prefer: str | None = None,
) -> Any:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer

    request = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        # Never log response bodies: Supabase diagnostics can contain private data.
        print("idea_flow_supabase_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("Idea Inbox storage is unavailable") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(
            "idea_flow_supabase_transport_error",
            {"method": method, "exception_type": type(exc).__name__},
        )
        raise RuntimeError("Idea Inbox storage is unavailable") from exc

    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Idea Inbox storage returned an invalid response") from exc


def _rpc(name: str, body: dict[str, object]) -> Any:
    return _supabase_request("POST", f"rpc/{name}", body=body)


def _send_telegram(token: str, chat_id: int, text: str) -> None:
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Telegram reply failed") from exc
    if not payload.get("ok"):
        raise RuntimeError("Telegram reply failed")


def _format_list(rows: list[dict[str, object]]) -> str:
    if not rows:
        return "ไม่มีไอเดียในรายการนี้"
    return "\n".join(f"#{row['id']} [{row['status']}] {row['title']}" for row in rows)


MINIBOSS_SCORE_VERSION = "miniboss_v0_rule"

def _miniboss_score(idea: str) -> dict[str, object]:
    """Deterministic V0 scorer so the pipeline works without a paid LLM key."""
    text = " ".join((idea or "").lower().split())

    def has_any(*terms: str) -> bool:
        return any(term in text for term in terms)

    audience_fit = 12
    if has_any("ai", "เครื่องมือ", "แอป", "ทำงาน", "ครีเอเตอร์", "creator", "affiliate"):
        audience_fit += 5
    if has_any("ประหยัดเวลา", "รายได้", "เงิน", "productivity", "งาน"):
        audience_fit += 3
    audience_fit = min(audience_fit, 20)

    hook_potential = 10
    if has_any("ฟรี", "ทดลอง", "จริง", "คุ้ม", "ได้ไหม", "แทนมนุษย์", "ไม่ต้อง"):
        hook_potential += 6
    if len(text) >= 35:
        hook_potential += 2
    if has_any("ai", "เครื่องมือ", "แอป"):
        hook_potential += 2
    hook_potential = min(hook_potential, 20)

    revenue_potential = 8
    if has_any("affiliate", "สินค้า", "product", "รายได้", "เงิน", "ขาย", "คอมมิชชั่น"):
        revenue_potential += 10
    if has_any("เครื่องมือ", "แอป", "tool", "software", "saas"):
        revenue_potential += 5
    if has_any("ฟรี", "ทดลอง"):
        revenue_potential += 2
    revenue_potential = min(revenue_potential, 25)

    trend_potential = 8
    if has_any("ai", "automation", "agent", "เครื่องมือ", "แอป"):
        trend_potential += 5
    if has_any("ทดลอง", "รีวิว", "เทียบ", "จริง"):
        trend_potential += 2
    trend_potential = min(trend_potential, 15)

    brand_fit = 6
    if has_any("ai", "เครื่องมือ", "แอป", "automation"):
        brand_fit += 2
    if has_any("ทดลอง", "ใช้จริง", "รายได้", "affiliate", "ประหยัดเวลา"):
        brand_fit += 2
    brand_fit = min(brand_fit, 10)

    production_ease = 7
    if has_any("เครื่องมือ", "แอป", "เว็บ", "website", "tool", "ai"):
        production_ease += 2
    if has_any("ทดลอง", "รีวิว", "สอน", "วิธี", "เทียบ"):
        production_ease += 1
    production_ease = min(production_ease, 10)

    breakdown = {
        "audience_fit": audience_fit,
        "hook_potential": hook_potential,
        "revenue_potential": revenue_potential,
        "trend_potential": trend_potential,
        "brand_fit": brand_fit,
        "production_ease": production_ease,
    }
    total = int(sum(breakdown.values()))
    decision = "SELECTED" if total >= 80 else "BACKLOG" if total >= 60 else "ARCHIVED"
    reason = (
        f"Audience {audience_fit}/20, Hook {hook_potential}/20, "
        f"Revenue {revenue_potential}/25, Trend {trend_potential}/15, "
        f"Brand {brand_fit}/10, Ease {production_ease}/10"
    )
    return {
        "score": total,
        "decision": decision,
        "breakdown": breakdown,
        "reason": reason,
        "version": MINIBOSS_SCORE_VERSION,
    }


class SupabaseIdeaFlowService:
    def __init__(self) -> None:
        self.mutation_committed = False

    def claim_update(self, update_id: int) -> dict[str, object]:
        result = _rpc("idea_flow_claim_telegram_update", {"p_update_id": update_id})
        if not isinstance(result, dict) or not isinstance(result.get("action"), str):
            raise RuntimeError("Idea Inbox storage returned an invalid update claim")
        return result

    def prepare_reply(self, update_id: int, response_text: str) -> None:
        _rpc(
            "idea_flow_prepare_telegram_reply",
            {"p_update_id": update_id, "p_response_text": response_text},
        )

    def prepare_result_reply(self, update_id: int, response_text: str) -> None:
        _rpc(
            "idea_flow_prepare_telegram_result_reply",
            {"p_update_id": update_id, "p_response_text": response_text},
        )

    def mark_delivered(self, update_id: int) -> None:
        _rpc("idea_flow_mark_telegram_delivered", {"p_update_id": update_id})

    def capture(self, body: str, *, actor: str, update_id: int) -> int:
        idea_id = int(
            _rpc(
                "idea_flow_capture",
                {
                    "p_body": body,
                    "p_source": "telegram",
                    "p_actor": actor,
                    "p_update_id": update_id,
                },
            )
        )
        self.mutation_committed = True
        return idea_id

    def score_content_job(self, idea_id: int) -> dict[str, object]:
        rows = _supabase_request(
            "GET",
            "content_jobs"
            f"?idea_flow_id=eq.{idea_id}"
            "&select=id,idea,status"
            "&limit=1",
        ) or []
        if not rows:
            raise RuntimeError("Content job was not created")
        row = rows[0]
        if row.get("status") != "NEW":
            return {
                "score": row.get("score"),
                "decision": row.get("status"),
                "breakdown": row.get("score_breakdown") or {},
                "reason": row.get("score_reason") or "already scored",
                "version": row.get("score_version") or MINIBOSS_SCORE_VERSION,
            }

        result = _miniboss_score(str(row.get("idea") or ""))
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}",
            body={
                "status": result["decision"],
                "score": result["score"],
                "score_breakdown": result["breakdown"],
                "score_reason": result["reason"],
                "score_version": result["version"],
                "scored_at": "now()",
            },
            prefer="return=representation",
        )
        # PostgREST does not evaluate SQL expressions inside JSON. If scored_at was rejected,
        # retry without it and let the database timestamp be filled by the follow-up RPC/migration.
        if updated is None:
            raise RuntimeError("MiniBoss score update failed")
        return result

    def persist_miniboss_result(
        self,
        update_id: int,
        idea_id: int,
        result: dict[str, object],
    ) -> None:
        encoded = urllib.parse.quote(str(update_id), safe="")
        _supabase_request(
            "PATCH",
            f"idea_flow_telegram_updates?update_id=eq.{encoded}&status=eq.PROCESSED",
            body={
                "result_json": {
                    "kind": "capture",
                    "idea_id": idea_id,
                    "status": "CAPTURED",
                    "content_job_status": result["decision"],
                    "miniboss_score": result["score"],
                    "miniboss_reason": result["reason"],
                    "miniboss_version": result["version"],
                }
            },
        )

    def list(self, status: str | None = None, limit: int = 30) -> list[dict[str, object]]:
        path = "idea_flow_ideas?select=id,title,status&order=id.desc"
        if status:
            encoded = urllib.parse.quote(status.upper(), safe="")
            path += f"&status=eq.{encoded}"
        path += f"&limit={limit}"
        return list(_supabase_request("GET", path) or [])

    def search(self, query: str, limit: int = 30) -> list[dict[str, object]]:
        query = query.strip()
        if not query:
            return []
        escaped = query.replace("*", "\\*").replace(",", "\\,")
        encoded = urllib.parse.quote(f"*{escaped}*", safe="*\\")
        path = (
            "idea_flow_ideas?select=id,title,status"
            f"&or=(title.ilike.{encoded},body.ilike.{encoded})"
            f"&order=id.desc&limit={limit}"
        )
        return list(_supabase_request("GET", path) or [])

    def get(self, idea_id: int) -> dict[str, object]:
        rows = _supabase_request(
            "GET",
            f"idea_flow_ideas?id=eq.{idea_id}&select=id,title,body,status&limit=1",
        ) or []
        if not rows:
            raise ValueError(f"Idea #{idea_id} not found")
        idea = dict(rows[0])
        evaluations = _supabase_request(
            "GET",
            "idea_flow_evaluations"
            f"?idea_id=eq.{idea_id}&select=weighted_score,signal&order=id.desc&limit=1",
        ) or []
        idea["latest_evaluation"] = evaluations[0] if evaluations else None
        return idea

    def history(self, idea_id: int) -> list[dict[str, object]]:
        self.get(idea_id)
        return list(
            _supabase_request(
                "GET",
                "idea_flow_events"
                f"?idea_id=eq.{idea_id}&select=event_type,from_status,to_status,created_at"
                "&order=id.asc&limit=100",
            )
            or []
        )

    def mark_researched(self, idea_id: int, research: str, *, actor: str, update_id: int) -> None:
        _rpc(
            "idea_flow_mark_researched",
            {
                "p_idea_id": idea_id,
                "p_research": research,
                "p_actor": actor,
                "p_update_id": update_id,
            },
        )
        self.mutation_committed = True

    def evaluate(
        self,
        idea_id: int,
        *,
        demand: int,
        feasibility: int,
        strategic_fit: int,
        notes: str,
        evaluator: str,
        update_id: int,
    ) -> dict[str, object]:
        result = _rpc(
            "idea_flow_evaluate",
            {
                "p_idea_id": idea_id,
                "p_demand": demand,
                "p_feasibility": feasibility,
                "p_strategic_fit": strategic_fit,
                "p_notes": notes,
                "p_evaluator": evaluator,
                "p_update_id": update_id,
            },
        )
        if not isinstance(result, dict):
            raise RuntimeError("Idea Inbox storage returned an invalid evaluation")
        self.mutation_committed = True
        return result

    def transition(
        self, idea_id: int, target: str, *, actor: str, reason: str, update_id: int
    ) -> None:
        _rpc(
            "idea_flow_transition",
            {
                "p_idea_id": idea_id,
                "p_to_status": target,
                "p_actor": actor,
                "p_reason": reason,
                "p_update_id": update_id,
            },
        )
        self.mutation_committed = True


def _format_mutation_result(result: dict[str, object]) -> str:
    kind = result.get("kind")
    idea_id = result.get("idea_id")
    if kind == "capture":
        score = result.get("miniboss_score")
        decision = result.get("content_job_status")
        if score is not None and decision:
            return (
                f"จับไว้แล้ว ✅ Idea #{idea_id}\n"
                f"MiniBoss: {score}/100 → {decision}\n"
                f"{result.get('miniboss_reason') or ''}"
            ).strip()
        return f"จับไว้แล้ว ✅ Idea #{idea_id}\nสถานะ: CAPTURED"
    if kind == "research":
        return f"#{idea_id} -> RESEARCHED ✅"
    if kind == "evaluate":
        return (
            f"#{idea_id} EVALUATED ✅\nScore: {result['weighted_score']}/5"
            f"\nSignal: {result['signal']}"
        )
    if kind == "transition":
        return f"#{idea_id} -> {result['status']} ✅"
    raise RuntimeError("Idea Inbox storage returned an invalid mutation result")


def handle_text(
    service: SupabaseIdeaFlowService, text: str, *, actor: str, update_id: int
) -> str:
    text = (text or "").strip()
    if not text:
        return "ข้อความว่าง"
    if not text.startswith("/"):
        idea_id = service.capture(text, actor=actor, update_id=update_id)
        try:
            result = service.score_content_job(idea_id)
            service.persist_miniboss_result(update_id, idea_id, result)
            return (
                f"จับไว้แล้ว ✅ Idea #{idea_id}\n"
                f"MiniBoss: {result['score']}/100 → {result['decision']}\n"
                f"{result['reason']}"
            )
        except Exception as exc:
            print("miniboss_score_error", {"exception_type": type(exc).__name__})
            return (
                f"จับไว้แล้ว ✅ Idea #{idea_id}\n"
                "MiniBoss: รอประเมิน (ระบบ scoring ยังไม่พร้อม)"
            )

    parts = text.split()
    cmd = parts[0].split("@")[0].lower()
    if cmd in {"/help", "/start"}:
        return HELP
    if cmd == "/list":
        return _format_list(service.list(parts[1] if len(parts) > 1 else None))
    if cmd == "/search":
        return _format_list(service.search(" ".join(parts[1:])))
    if cmd == "/view":
        idea = service.get(int(parts[1]))
        evaluation = idea["latest_evaluation"]
        extra = ""
        if evaluation:
            extra = f"\nScore: {evaluation['weighted_score']}/5\nSignal: {evaluation['signal']}"
        return f"#{idea['id']} [{idea['status']}]\n{idea['body']}{extra}"
    if cmd == "/history":
        events = service.history(int(parts[1]))
        return "\n".join(
            f"{event['created_at']} | {event['event_type']} | "
            f"{event.get('from_status') or '-'} -> {event.get('to_status') or '-'}"
            for event in events[-20:]
        )
    if cmd == "/research":
        if len(parts) < 3:
            return "ใช้: /research ID TEXT"
        idea_id = int(parts[1])
        service.mark_researched(
            idea_id, " ".join(parts[2:]), actor=actor, update_id=update_id
        )
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
            update_id=update_id,
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
        if len(parts) < 2:
            return f"ใช้: {cmd} ID [reason]"
        idea_id = int(parts[1])
        target = transitions[cmd]
        service.transition(
            idea_id,
            target,
            actor=actor,
            reason=" ".join(parts[2:]),
            update_id=update_id,
        )
        return f"#{idea_id} -> {target} ✅"
    return "ไม่รู้จักคำสั่ง\n\n" + HELP


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    try:
        expected_secret = _required_env("TELEGRAM_WEBHOOK_SECRET")
        token = _required_env("TELEGRAM_BOT_TOKEN")
        allowed_chat_id = _required_env("TELEGRAM_ALLOWED_CHAT_ID")
        _required_env("SUPABASE_URL")
        _required_env("SUPABASE_SECRET_KEY")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Idea Inbox is not configured") from exc

    supplied_secret = x_telegram_bot_api_secret_token or ""
    if not secrets.compare_digest(supplied_secret, expected_secret):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        update = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Telegram update") from exc

    update_id = update.get("update_id")
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=400, detail="Invalid Telegram update")
    if chat_id is None or str(chat_id) != allowed_chat_id or not isinstance(text, str):
        return {"ok": True}

    service = SupabaseIdeaFlowService()
    claim = await asyncio.to_thread(service.claim_update, update_id)
    action = claim["action"]
    if action == "DELIVERED":
        return {"ok": True}
    if action == "BUSY":
        # A non-2xx response keeps Telegram retrying until the processing lease expires.
        raise HTTPException(status_code=503, detail="Idea Inbox update is processing")

    if action == "RETRY_REPLY":
        reply = claim.get("response_text")
        if not isinstance(reply, str) or not reply:
            raise HTTPException(status_code=503, detail="Idea Inbox retry state is invalid")
    elif action == "RESUME_RESULT":
        result = claim.get("result")
        if not isinstance(result, dict):
            raise HTTPException(status_code=503, detail="Idea Inbox result state is invalid")
        reply = _format_mutation_result(result)
        await asyncio.to_thread(service.prepare_result_reply, update_id, reply)
    elif action == "PROCESS":
        actor = f"telegram:{chat_id}"
        command_succeeded = False
        try:
            reply = await asyncio.to_thread(
                handle_text, service, text, actor=actor, update_id=update_id
            )
            command_succeeded = True
        except Exception as exc:
            # Keep details out of HTTP responses and logs; the user receives a generic error.
            print("idea_flow_command_error", {"exception_type": type(exc).__name__})
            reply = "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองส่งคำสั่งใหม่"
        prepare = (
            service.prepare_result_reply
            if command_succeeded and service.mutation_committed
            else service.prepare_reply
        )
        await asyncio.to_thread(prepare, update_id, reply)
    else:
        raise HTTPException(status_code=503, detail="Idea Inbox update state is invalid")

    # A failed Telegram call leaves the durable READY reply available for the retry.
    await asyncio.to_thread(_send_telegram, token, int(chat_id), reply)
    await asyncio.to_thread(service.mark_delivered, update_id)
    return {"ok": True}
