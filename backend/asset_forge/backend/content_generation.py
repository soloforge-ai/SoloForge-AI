"""Autonomous content generation worker for SoloForge content_jobs."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GENERATOR_VERSION = "content_gen_v0.1"
SYSTEM_PROMPT = """You are SoloForge Content Strategist for the Ai HackWork brand.
Create concise Thai short-form video content for TikTok.
Return ONLY one JSON object with these keys:
hook, script, caption, cta, onscreen_text, visual_prompt, motion_prompt, risk_level.
Rules:
- 30-45 second vertical video.
- Hook must be immediate and specific.
- Do not invent personal-use claims, income claims, test results, prices, discounts, or product facts.
- If the idea says to test or compare something but no evidence is supplied, frame it as a test plan, not as completed experience.
- risk_level must be LOW, MEDIUM, or HIGH.
- onscreen_text must be an array of short strings.
- visual_prompt and motion_prompt should be production-ready.
"""

PROVIDERS = [
    ("gemini", "GEMINI_API_KEY", "GEMINI_MODEL",
     "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"),
    ("groq", "GROQ_API_KEY", "GROQ_MODEL",
     "openai/gpt-oss-120b", "https://api.groq.com/openai/v1/chat/completions"),
    ("openrouter", "OPENROUTER_API_KEY", "OPENROUTER_MODEL",
     "openrouter/free", "https://openrouter.ai/api/v1/chat/completions"),
    ("pollinations", "POLLINATIONS_API_KEY", "POLLINATIONS_TEXT_MODEL",
     "openai", "https://gen.pollinations.ai/v1/chat/completions"),
]


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _supabase_request(method: str, path: str, body: dict[str, object] | None = None,
                      prefer: str | None = None) -> Any:
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
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer
    req = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print("content_worker_supabase_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("Content storage unavailable") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Content storage unavailable") from exc
    return json.loads(raw.decode("utf-8")) if raw else None


def _send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
    except Exception as exc:
        print("content_worker_telegram_error", {"exception_type": type(exc).__name__})


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1).replace("```", "").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model did not return JSON")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model JSON must be an object")
    required = ["hook", "script", "caption", "cta", "onscreen_text",
                "visual_prompt", "motion_prompt", "risk_level"]
    if any(key not in value for key in required):
        raise ValueError("Model JSON missing required fields")
    if value["risk_level"] not in {"LOW", "MEDIUM", "HIGH"}:
        value["risk_level"] = "MEDIUM"
    if not isinstance(value["onscreen_text"], list):
        value["onscreen_text"] = [str(value["onscreen_text"])]
    return value


def _call_provider(idea: str) -> tuple[dict[str, Any], str, str] | None:
    for provider, key_env, model_env, default_model, endpoint in PROVIDERS:
        api_key = os.getenv(key_env, "").strip()
        if not api_key:
            continue
        model = os.getenv(model_env, default_model).strip() or default_model
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"IDEA:\n{idea}"},
            ],
            "temperature": 0.35,
            "max_tokens": 1600,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if provider == "openrouter":
            headers["X-OpenRouter-Title"] = "SoloForge Content Worker"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return _extract_json(content), provider, model
        except Exception as exc:
            print("content_provider_error", {
                "provider": provider,
                "exception_type": type(exc).__name__,
            })
    return None


def _fallback_package(idea: str) -> dict[str, Any]:
    return {
        "hook": f"เครื่องมือนี้จะช่วยประหยัดเวลาได้จริงแค่ไหน? มาลองจากโจทย์นี้: {idea[:70]}",
        "script": (
            "วันนี้เราจะทดสอบแบบไม่อวยก่อนว่าเครื่องมือแนวนี้ช่วยลดเวลางานได้จริงไหม "
            "เริ่มจากกำหนดงานเดิมหนึ่งชิ้น จับเวลาก่อนใช้ จากนั้นลองใช้ AI หรือเครื่องมือที่เกี่ยวข้อง "
            "แล้วเทียบเวลาที่ใช้ คุณภาพผลลัพธ์ และจุดที่ยังต้องแก้เอง "
            "ถ้าผลต่างชัดค่อยสรุปว่าเหมาะกับใคร ไม่เหมาะกับใคร และควรใช้ตอนไหน"
        ),
        "caption": (
            "จะรีวิวเครื่องมือแบบไม่เดา: เทียบเวลา คุณภาพ และงานที่ยังต้องแก้เองก่อนสรุปว่าใช้จริงคุ้มไหม"
        ),
        "cta": "อยากให้ทดสอบเครื่องมือไหนต่อ ส่งชื่อมาได้เลย",
        "onscreen_text": [
            "ช่วยประหยัดเวลาได้จริงไหม?",
            "จับเวลาก่อนใช้",
            "ทดลองกับงานจริง",
            "เทียบเวลา + คุณภาพ",
            "ค่อยสรุปว่าคุ้มไหม",
        ],
        "visual_prompt": (
            "Vertical 9:16 modern AI productivity test, laptop and phone UI, timer, clean desk, "
            "Thai creator-tech aesthetic, crisp interface closeups, no fake brand claims"
        ),
        "motion_prompt": (
            "Fast clean cuts, timer animation, screen-recording style inserts, subtle zooms, "
            "kinetic Thai captions, 30-45 seconds"
        ),
        "risk_level": "LOW",
    }


def _claim_selected(limit: int = 2) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.SELECTED"
        "&select=id,idea_flow_id,idea,status,retry_count"
        f"&order=created_at.asc&limit={limit}",
    ) or []
    claimed: list[dict[str, Any]] = []
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.SELECTED",
            body={"status": "GENERATING", "error_message": None},
            prefer="return=representation",
        ) or []
        if updated:
            claimed.append(dict(updated[0]))
    return claimed


def _finish_job(job: dict[str, Any], package: dict[str, Any],
                provider: str, model: str) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}&status=eq.GENERATING",
        body={
            "status": "READY_FOR_REVIEW",
            "hook": str(package["hook"]),
            "script": str(package["script"]),
            "caption": str(package["caption"]),
            "cta": str(package["cta"]),
            "onscreen_text": package["onscreen_text"],
            "visual_prompt": str(package["visual_prompt"]),
            "motion_prompt": str(package["motion_prompt"]),
            "risk_level": str(package["risk_level"]),
            "qa_status": "PENDING",
            "content_package": package,
            "generator_provider": provider,
            "generator_model": model,
            "generator_version": GENERATOR_VERSION,
            "generated_at": None,
            "error_message": None,
        },
    )
    # generated_at is filled separately because PostgREST JSON cannot express SQL now().
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={"generator_version": GENERATOR_VERSION},
    )


def _fail_job(job: dict[str, Any], exc: Exception) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    retry_count = int(job.get("retry_count") or 0) + 1
    status = "SELECTED" if retry_count <= 2 else "GENERATION_FAILED"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={
            "status": status,
            "retry_count": retry_count,
            "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
        },
    )


def process_selected_once() -> int:
    processed = 0
    for job in _claim_selected():
        idea_id = job.get("idea_flow_id") or "?"
        try:
            result = _call_provider(str(job.get("idea") or ""))
            if result is None:
                package, provider, model = _fallback_package(str(job.get("idea") or "")), "template_fallback", "v0"
            else:
                package, provider, model = result
            _finish_job(job, package, provider, model)
            _send_telegram(
                f"✍️ Job #{idea_id} — READY_FOR_REVIEW\n"
                f"Hook: {package['hook']}\n\n"
                f"ใช้ /job {idea_id} เพื่อตรวจสถานะ"
            )
            processed += 1
        except Exception as exc:
            print("content_generation_error", {
                "idea_flow_id": idea_id,
                "exception_type": type(exc).__name__,
            })
            _fail_job(job, exc)
    return processed


async def content_worker_loop() -> None:
    await asyncio.sleep(3)
    while True:
        try:
            await asyncio.to_thread(process_selected_once)
        except Exception as exc:
            print("content_worker_loop_error", {"exception_type": type(exc).__name__})
        await asyncio.sleep(30)
