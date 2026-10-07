"""Combined Telegram webhook: Idea Inbox + Sales Inbox actions."""

from __future__ import annotations

import asyncio
import json
import secrets
from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request

try:
    from backend.idea_flow_webhook import (
        SupabaseIdeaFlowService,
        _required_env,
        _format_mutation_result,
        _format_job,
        handle_text,
    )
    from backend.sales_inbox import (
        SalesLeadService,
        answer_callback,
        format_lead,
        format_sales_list,
        lead_keyboard,
        parse_addlead,
        send_message,
    )
    from backend.content_jobs_api import _resume_job
except ImportError:
    from backend.asset_forge.backend.idea_flow_webhook import (
        SupabaseIdeaFlowService,
        _required_env,
        _format_mutation_result,
        _format_job,
        handle_text,
    )
    from backend.asset_forge.backend.sales_inbox import (
        SalesLeadService,
        answer_callback,
        format_lead,
        format_sales_list,
        lead_keyboard,
        parse_addlead,
        send_message,
    )
    from backend.asset_forge.backend.content_jobs_api import _resume_job

router = APIRouter(prefix="/telegram/idea-inbox", tags=["idea-inbox", "sales-inbox"])


_CONTENT_RESUMABLE_STATUSES = {"APPROVED", "ASSET_QUEUED", "ASSET_READY", "AUDIO_READY"}


def content_job_keyboard(job: dict[str, object]) -> dict[str, object] | None:
    status = str(job.get("status") or "")
    if status not in _CONTENT_RESUMABLE_STATUSES:
        return None
    package = dict(job.get("content_package") or {})
    route = str(package.get("pipeline_route") or "").strip().upper()
    if status != "APPROVED" and route != "VIDEO":
        return None
    job_id = str(job.get("id") or "").strip()
    if not job_id:
        return None
    return {
        "inline_keyboard": [[
            {"text": "▶️ รันต่อ", "callback_data": f"content:continue:{job_id}"}
        ]]
    }


def _content_callback(
    data: str,
    *,
    background_tasks: BackgroundTasks,
) -> tuple[str, dict[str, object] | None, str]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "content" or parts[1] != "continue":
        raise ValueError("Invalid content action")

    job_id = parts[2].strip()
    service = SupabaseIdeaFlowService()
    job = service.get_content_job(job_id)
    status = str(job.get("status") or "")

    if status not in _CONTENT_RESUMABLE_STATUSES:
        raise ValueError(f"Job รันต่อไม่ได้จากสถานะ {status}")

    package = dict(job.get("content_package") or {})
    route = str(package.get("pipeline_route") or "").strip().upper()
    if status != "APPROVED" and route != "VIDEO":
        raise ValueError("รันต่อรองรับเฉพาะ VIDEO job หลัง routing แล้ว")

    background_tasks.add_task(_resume_job, job_id, status)

    reply = (
        f"{_format_job(job)}\n\n"
        "▶️ รับคำสั่งรันต่อแล้ว\n"
        "การอนุมัติ/Proof รอบถัดไปให้ตรวจใน ChatGPT ตามเดิม"
    )
    return reply, None, "เริ่มรันต่อแล้ว"


def _sales_message(text: str) -> tuple[str, dict | None] | None:
    clean = (text or "").strip()
    service = SalesLeadService()
    if clean.startswith("/sales"):
        return format_sales_list(service.list()), None
    if clean.startswith("/lead "):
        try:
            lead_id = int(clean.split()[1])
            lead = service.get(lead_id)
            return format_lead(lead), lead_keyboard(lead)
        except (ValueError, IndexError):
            return "ใช้: /lead ID", None
    if clean.startswith("/addlead"):
        try:
            payload = parse_addlead(clean)
            lead = service.create(**payload)
            return format_lead(lead), lead_keyboard(lead)
        except ValueError as exc:
            return str(exc), None
    return None


def _sales_callback(data: str) -> tuple[str, dict | None, str]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "sales":
        raise ValueError("Invalid sales action")
    action = parts[1]
    lead_id = int(parts[2])
    service = SalesLeadService()
    if action == "prepare":
        lead = service.prepare(lead_id)
        return format_lead(lead), lead_keyboard(lead), "สร้างข้อเสนอแล้ว"
    if action == "skip":
        lead = service.skip(lead_id)
        return format_lead(lead), lead_keyboard(lead), "ข้าม Lead นี้แล้ว"
    if action == "send":
        lead = service.get(lead_id)
        if str(lead.get("status") or "") != "READY_TO_SEND":
            raise ValueError("Lead ยังไม่พร้อมส่ง")
        result = send_sales_email(lead)
        updated = service.get(lead_id)
        return (
            format_lead(updated) + f"\n\n✅ ส่งอีเมลแล้ว → {result['recipient']}",
            lead_keyboard(updated),
            "ส่งอีเมลแล้ว",
        )
    raise ValueError("Unknown sales action")


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
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
    if not isinstance(update_id, int):
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

    callback = update.get("callback_query") or {}
    if callback:
        callback_id = callback.get("id")
        data = callback.get("data")
        message = callback.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id is None or str(chat_id) != allowed_chat_id or not isinstance(data, str):
            return {"ok": True}
        if not (data.startswith("sales:") or data.startswith("content:")):
            return {"ok": True}
        try:
            if data.startswith("content:"):
                reply, keyboard, toast = _content_callback(
                    data,
                    background_tasks=background_tasks,
                )
            else:
                reply, keyboard, toast = await asyncio.to_thread(_sales_callback, data)
            await asyncio.to_thread(send_message, token, int(chat_id), reply, keyboard)
            if isinstance(callback_id, str):
                await asyncio.to_thread(answer_callback, token, callback_id, toast)
        except Exception as exc:
            print("sales_callback_error", {"exception_type": type(exc).__name__})
            if isinstance(callback_id, str):
                await asyncio.to_thread(answer_callback, token, callback_id, "ทำรายการไม่สำเร็จ")
        return {"ok": True}

    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text")
    if chat_id is None or str(chat_id) != allowed_chat_id or not isinstance(text, str):
        return {"ok": True}

    service = SupabaseIdeaFlowService()
    claim = await asyncio.to_thread(service.claim_update, update_id)
    action = claim["action"]
    if action == "DELIVERED":
        return {"ok": True}
    if action == "BUSY":
        raise HTTPException(status_code=503, detail="Idea Inbox update is processing")

    keyboard = None
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
            sales = await asyncio.to_thread(_sales_message, text)
            if sales is not None:
                reply, keyboard = sales
            else:
                reply = await asyncio.to_thread(handle_text, service, text, actor=actor, update_id=update_id)
                clean = text.strip()
                parts = clean.split()
                cmd = parts[0].split("@")[0].lower() if parts else ""
                try:
                    if cmd == "/job" and len(parts) >= 2:
                        keyboard = content_job_keyboard(service.get_content_job(parts[1]))
                    elif cmd == "/latest":
                        keyboard = content_job_keyboard(service.latest_content_job())
                except Exception:
                    keyboard = None
            command_succeeded = True
        except Exception as exc:
            print("telegram_command_error", {"exception_type": type(exc).__name__})
            reply = "เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่"
        prepare = service.prepare_result_reply if command_succeeded and service.mutation_committed else service.prepare_reply
        await asyncio.to_thread(prepare, update_id, reply)
    else:
        raise HTTPException(status_code=503, detail="Idea Inbox update state is invalid")

    await asyncio.to_thread(send_message, token, int(chat_id), reply, keyboard)
    await asyncio.to_thread(service.mark_delivered, update_id)
    return {"ok": True}
