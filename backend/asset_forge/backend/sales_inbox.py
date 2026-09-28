"""SoloForge Telegram Sales Inbox v1."""

from __future__ import annotations
import json
import os
import urllib.parse
import urllib.request
from typing import Any

try:\n    from backend.idea_flow_webhook import _supabase_request\nexcept ImportError:\n    from backend.asset_forge.backend.idea_flow_webhook import _supabase_request

PROVIDERS = [
    ("gemini", "GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash",
     "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
    ("groq", "GROQ_API_KEY", "GROQ_MODEL", "openai/gpt-oss-120b",
     "https://api.groq.com/openai/v1/chat/completions"),
    ("openrouter", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openrouter/free",
     "https://openrouter.ai/api/v1/chat/completions"),
]

SYSTEM_PROMPT = """You are SoloForge Sales Agent.
Write concise professional Thai B2B outreach.
Return ONLY one JSON object with keys subject, body, offer.
Use only supplied facts. Never invent ROI, savings, results, prices, or client history.
Keep first outreach under 120 Thai words and end with a low-friction next step.
"""


def score_lead(company: str, need: str, evidence: str, contact: str) -> int:
    text = " ".join([company, need, evidence, contact]).lower()
    score = 35
    for term in ("หา freelancer","หาคนทำ","ต้องการ","dashboard","power bi","excel",
                 "power query","automation","report","รายงาน","วิเคราะห์ข้อมูล"):
        if term in text:
            score += 7
    for term in ("manual","ประจำสัปดาห์","ประจำเดือน","เสียเวลา","หลายไฟล์","รวมข้อมูล"):
        if term in text:
            score += 5
    if contact.strip():
        score += 10
    return min(100, score)


def _extract_json(text: str) -> dict[str, str]:
    cleaned = text.strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model did not return JSON")
        data = json.loads(cleaned[start:end + 1])
    return {
        "subject": str(data.get("subject") or "ขอเสนอช่วยจัดระบบงานรายงาน"),
        "body": str(data.get("body") or ""),
        "offer": str(data.get("offer") or "Excel / Power Query / Dashboard Automation"),
    }


def draft_outreach(lead: dict[str, Any]) -> dict[str, str]:
    context = (
        f"Company: {lead.get('company') or '-'}\n"
        f"Contact: {lead.get('contact_name') or '-'}\n"
        f"Channel: {lead.get('contact_channel') or '-'}\n"
        f"Need: {lead.get('need') or '-'}\n"
        f"Evidence: {lead.get('evidence') or '-'}"
    )
    for provider, key_env, model_env, default_model, endpoint in PROVIDERS:
        key = os.getenv(key_env, "").strip()
        if not key:
            continue
        payload = {
            "model": os.getenv(model_env, default_model).strip() or default_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            "temperature": 0.25,
            "max_tokens": 900,
        }
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if provider == "openrouter":
            headers["X-OpenRouter-Title"] = "SoloForge Sales Agent"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            return _extract_json(body["choices"][0]["message"]["content"])
        except Exception as exc:
            print("sales_provider_error", {"provider": provider, "exception_type": type(exc).__name__})

    company = str(lead.get("company") or "ทีมงาน")
    need = str(lead.get("need") or "งานรายงานและข้อมูล")
    return {
        "subject": f"ขอเสนอช่วยจัดระบบ {need[:45]}",
        "offer": "Excel / Power Query / Dashboard Automation",
        "body": (
            f"สวัสดีค่ะ ทีม {company}\n\n"
            f"เห็นว่ามีโจทย์เกี่ยวกับ {need} "
            "เราให้บริการจัดระบบ Excel, Power Query และ Dashboard เพื่อลดขั้นตอนงานรายงานที่ต้องทำซ้ำ "
            "หากสะดวก สามารถส่งตัวอย่างไฟล์หรือ workflow ปัจจุบันมาได้ เราจะช่วยสรุปแนวทางที่เหมาะสมให้ก่อนค่ะ"
        ),
    }


class SalesLeadService:
    def create(self, source: str, company: str, need: str, evidence: str = "",
               contact_channel: str = "", contact_name: str = "", source_ref: str = "") -> dict[str, Any]:
        score = score_lead(company, need, evidence, contact_channel)
        rows = _supabase_request("POST", "sales_leads", body={
            "source": source or "manual",
            "source_ref": source_ref or None,
            "company": company or None,
            "contact_name": contact_name or None,
            "contact_channel": contact_channel or None,
            "need": need,
            "evidence": evidence or None,
            "score": score,
            "status": "QUALIFIED" if score >= 65 else "NEW",
        }, prefer="return=representation") or []
        if not rows:
            raise RuntimeError("Could not create sales lead")
        return dict(rows[0])

    def list(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = _supabase_request(
            "GET",
            "sales_leads?select=id,source,company,need,score,status,contact_channel,created_at"
            f"&order=score.desc,created_at.desc&limit={limit}",
        ) or []
        return [dict(row) for row in rows]

    def get(self, lead_id: int) -> dict[str, Any]:
        rows = _supabase_request(
            "GET",
            f"sales_leads?id=eq.{lead_id}&select=id,source,source_ref,company,contact_name,"
            "contact_channel,need,evidence,offer,score,status,outreach_subject,outreach_body,"
            "created_at,updated_at&limit=1",
        ) or []
        if not rows:
            raise ValueError(f"Lead #{lead_id} not found")
        return dict(rows[0])

    def prepare(self, lead_id: int) -> dict[str, Any]:
        lead = self.get(lead_id)
        draft = draft_outreach(lead)
        rows = _supabase_request("PATCH", f"sales_leads?id=eq.{lead_id}", body={
            "status": "READY_TO_SEND",
            "outreach_subject": draft["subject"],
            "outreach_body": draft["body"],
            "offer": draft["offer"],
            "last_error": None,
        }, prefer="return=representation") or []
        if not rows:
            raise RuntimeError("Could not prepare outreach")
        return dict(rows[0])

    def skip(self, lead_id: int) -> dict[str, Any]:
        rows = _supabase_request("PATCH", f"sales_leads?id=eq.{lead_id}",
                                 body={"status": "SKIPPED"}, prefer="return=representation") or []
        if not rows:
            raise ValueError(f"Lead #{lead_id} not found")
        return dict(rows[0])


def format_lead(lead: dict[str, Any]) -> str:
    text = (
        f"🔥 Lead #{lead['id']}\n\n"
        f"Company: {lead.get('company') or '-'}\n"
        f"Source: {lead.get('source') or '-'}\n"
        f"Need: {lead.get('need') or '-'}\n"
        f"Evidence: {lead.get('evidence') or '-'}\n"
        f"Contact: {lead.get('contact_name') or '-'} / {lead.get('contact_channel') or '-'}\n"
        f"Lead Score: {lead.get('score') or 0}/100\n"
        f"Status: {lead.get('status') or '-'}"
    )
    if lead.get("outreach_body"):
        text += (
            f"\n\n📩 Outreach Draft\nSubject: {lead.get('outreach_subject') or '-'}\n\n"
            f"{lead.get('outreach_body')}"
        )
    return text[:3900]


def format_sales_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "ยังไม่มี Sales Lead"
    lines = ["💰 SoloForge Sales Inbox", ""]
    for row in rows:
        need = str(row.get("need") or "").replace("\n", " ")
        if len(need) > 60:
            need = need[:57] + "..."
        lines += [f"#{row['id']}  {row.get('score',0)}/100 [{row.get('status')}]",
                  str(row.get("company") or "-"), need, ""]
    return "\n".join(lines).strip()


def lead_keyboard(lead: dict[str, Any]) -> dict[str, Any]:
    lead_id = int(lead["id"])
    status = str(lead.get("status") or "")
    buttons: list[list[dict[str, str]]] = []
    if status not in {"READY_TO_SEND","CONTACTED","REPLIED","WON","LOST","SKIPPED"}:
        buttons.append([
            {"text": "📩 เตรียมข้อเสนอ", "callback_data": f"sales:prepare:{lead_id}"},
            {"text": "⏭ ข้าม", "callback_data": f"sales:skip:{lead_id}"},
        ])
    elif status == "READY_TO_SEND":
        buttons.append([
            {"text": "📤 ส่งอีเมล", "callback_data": f"sales:send:{lead_id}"},
            {"text": "⏭ ข้าม", "callback_data": f"sales:skip:{lead_id}"},
        ])
    return {"inline_keyboard": buttons}


def parse_addlead(text: str) -> dict[str, str]:
    parts = [p.strip() for p in text[len("/addlead"):].strip().split("|")]
    if len(parts) < 3:
        raise ValueError("ใช้: /addlead SOURCE | COMPANY | NEED | EVIDENCE | CONTACT_CHANNEL | CONTACT_NAME | SOURCE_REF")
    while len(parts) < 7:
        parts.append("")
    keys = ["source","company","need","evidence","contact_channel","contact_name","source_ref"]
    return dict(zip(keys, parts))


def send_message(token: str, chat_id: int, text: str, keyboard: dict[str, Any] | None = None) -> None:
    payload = {"chat_id": str(chat_id), "text": text[:4000]}
    if keyboard is not None:
        payload["reply_markup"] = json.dumps(keyboard, ensure_ascii=False)
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError("Telegram reply failed")


def answer_callback(token: str, callback_query_id: str, text: str = "") -> None:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/answerCallbackQuery",
        data=urllib.parse.urlencode({"callback_query_id": callback_query_id, "text": text[:180]}).encode("utf-8"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
    except Exception:
        pass
