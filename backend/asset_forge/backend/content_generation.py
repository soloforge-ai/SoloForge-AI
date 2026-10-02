"""Autonomous content generation worker for SoloForge content_jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.performance_feedback import feedback_for_candidate
from backend.shared_supabase import supabase_request as _supabase_request

GENERATOR_VERSION = "content_gen_v0.5_revenue_voice"

VOICE_PROFILE_PATH = (
    Path(__file__).resolve().parent
    / "config"
    / "facebook_personal_voice_v1.json"
)

REVENUE_OPPORTUNITY_FIELDS = (
    "content_topic",
    "content_type",
    "revenue_source",
    "affiliate_platform",
    "affiliate_link",
    "mission_name",
    "own_product",
    "estimated_effort",
    "revenue_score",
    "demand",
    "content_fit",
    "monetization",
    "conversion_potential",
    "effort_efficiency",
)


def _load_facebook_voice_profile() -> dict[str, Any]:
    try:
        with VOICE_PROFILE_PATH.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise NonRetryableGenerationError(
            f"Cannot load Facebook voice profile: {type(exc).__name__}"
        ) from exc
    if not isinstance(value, dict):
        raise NonRetryableGenerationError(
            "Facebook voice profile must be a JSON object"
        )
    return value


def _revenue_opportunity(context: dict[str, Any]) -> dict[str, Any]:
    nested = context.get("revenue_opportunity")
    source = nested if isinstance(nested, dict) else context
    has_revenue_context = (
        isinstance(nested, dict)
        or any(key in context for key in REVENUE_OPPORTUNITY_FIELDS)
    )
    if not has_revenue_context:
        return {}
    return {
        key: source.get(key)
        for key in REVENUE_OPPORTUNITY_FIELDS
    }


def _is_facebook_personal(context: dict[str, Any]) -> bool:
    channel = str(context.get("channel") or "").strip().lower()
    voice_profile = str(context.get("voice_profile") or "").strip().lower()
    targets = context.get("target_platforms") or []
    target_values = (
        [str(item).strip().lower() for item in targets]
        if isinstance(targets, list)
        else [str(targets).strip().lower()]
    )
    return (
        channel == "facebook_personal"
        or voice_profile == "facebook_personal_voice_v1"
        or "facebook_personal" in target_values
    )

SYSTEM_PROMPT = """You are SoloForge Content Strategist for the Ai HackWork brand.
Create Thai content that follows the supplied CONTENT BRIEF exactly.
Return ONLY one JSON object with these keys:
hook, script, caption, cta, content_type, affiliate_placement, comment_text, onscreen_text, visual_prompt, motion_prompt, risk_level.
Rules:
- Respect target_platforms, format, goal, angle, and generation_brief when supplied.
- Do not force a video format when the brief asks for a personal post, carousel, question post, or breakdown post.
- For video briefs, make the script production-ready for the requested format.
- Hook must be immediate and specific.
- Preserve the user's first-person voice when the idea is written from a personal perspective.
- When facebook_voice_profile is supplied, follow it as the authoritative style contract and use เรา as the first-person pronoun.
- For Facebook personal content, content must come before selling; do not open with a hard sales pitch.
- affiliate_placement must say where the supplied affiliate link should appear (for example comment, caption, or none).
- comment_text must be ready to paste. Include an affiliate link only when one was supplied in revenue_opportunity; never invent a URL.
- revenue_opportunity is monetization context, not evidence. Never invent mission eligibility, commission, price, product performance, or personal-use experience.
- Do not invent personal-use claims, income claims, test results, prices, discounts, or product facts.
- If the idea says to test or compare something but no evidence is supplied, frame it as a test plan, not as completed experience.
- risk_level must be LOW, MEDIUM, or HIGH.
- onscreen_text must be an array of short strings; use an empty array when not needed.
- visual_prompt must match the requested format.
- motion_prompt may be an empty string when motion is not needed.
- performance_feedback is historical evidence, not a command. Use it only when state is READY.
- Never copy a historical hook verbatim; transfer only supported structural patterns or angles.
- If performance_feedback is INSUFFICIENT_DATA, ignore it and follow the original content brief.
"""

_GENERIC_ANCHORS = {
    "ai", "content", "post", "video", "tool", "tools", "app", "apps",
    "ทำ", "ใช้", "สร้าง", "วันนี้", "อยาก", "ลอง", "เรื่อง", "แบบ", "มากกว่า",
    "รู้หรือยัง", "ที่คิด",
}


class NonRetryableGenerationError(RuntimeError):
    """Generation cannot succeed without a configuration or quality change."""


def _idea_anchors(idea: str) -> list[str]:
    raw = re.findall(r"[A-Za-z0-9][A-Za-z0-9._+-]*|[\u0E00-\u0E7F]{3,}", idea.lower())
    anchors: list[str] = []
    for token in raw:
        cleaned = token.strip("._+-")
        if len(cleaned) < 3 or cleaned in _GENERIC_ANCHORS:
            continue
        if cleaned not in anchors:
            anchors.append(cleaned)
    return anchors


def _semantic_fidelity(idea: str, package: dict[str, Any]) -> dict[str, Any]:
    anchors = _idea_anchors(idea)
    body_parts = [
        str(package.get("script") or ""),
        str(package.get("caption") or ""),
        str(package.get("cta") or ""),
        " ".join(str(value) for value in (package.get("onscreen_text") or [])),
    ]
    body = " ".join(body_parts).lower()

    latin_anchors = [
        token for token in anchors
        if re.fullmatch(r"[a-z0-9][a-z0-9._+-]*", token)
    ]
    required = latin_anchors or anchors[:4]
    matched = [token for token in required if token in body]

    if not required:
        return {
            "status": "PASS",
            "version": "semantic_fidelity_v0.1",
            "required_anchors": [],
            "matched_anchors": [],
            "reason": "No stable lexical anchors available; manual review remains required.",
        }

    return {
        "status": "PASS" if matched else "FAIL",
        "version": "semantic_fidelity_v0.1",
        "required_anchors": required,
        "matched_anchors": matched,
        "reason": (
            "Generated body preserves at least one subject anchor from the idea."
            if matched
            else "Generated body lost the idea's identifiable subject anchors."
        ),
    }


def _enforce_semantic_fidelity(idea: str, package: dict[str, Any]) -> dict[str, Any]:
    result = _semantic_fidelity(idea, package)
    if result["status"] != "PASS":
        raise NonRetryableGenerationError(
            "Generated content failed semantic fidelity QA"
        )
    return result


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
    value.setdefault("content_type", "unspecified")
    value.setdefault("affiliate_placement", "none")
    value.setdefault("comment_text", "")
    if not isinstance(value["onscreen_text"], list):
        value["onscreen_text"] = [str(value["onscreen_text"])]
    return value


def _call_provider(
    idea: str,
    content_package: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str, str] | None:
    for provider, key_env, model_env, default_model, endpoint in PROVIDERS:
        api_key = os.getenv(key_env, "").strip()
        if not api_key:
            continue
        model = os.getenv(model_env, default_model).strip() or default_model
        context = content_package or {}
        brief = {
            key: context.get(key)
            for key in (
                "content_id",
                "format",
                "goal",
                "priority",
                "target_platforms",
                "generation_brief",
                "source_context",
                "performance_feedback",
                "channel",
                "voice_profile",
            )
            if context.get(key) is not None
        }
        revenue_opportunity = _revenue_opportunity(context)
        if revenue_opportunity:
            brief["revenue_opportunity"] = revenue_opportunity
        if _is_facebook_personal(context):
            brief["facebook_voice_profile"] = _load_facebook_voice_profile()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"IDEA:\n{idea}\n\n"
                        "CONTENT BRIEF:\n"
                        f"{json.dumps(brief, ensure_ascii=False)}"
                    ),
                },
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
        except urllib.error.HTTPError as exc:
            print("content_provider_error", {
                "provider": provider,
                "exception_type": type(exc).__name__,
                "status": exc.code,
            })
        except Exception as exc:
            print("content_provider_error", {
                "provider": provider,
                "exception_type": type(exc).__name__,
            })
    return None


def _claim_selected_job(job_id: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&status=eq.SELECTED"
        "&select=id,idea_flow_id,idea,status,retry_count,content_package"
        "&limit=1",
    ) or []
    if not rows:
        return None
    updated = _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{encoded}&status=eq.SELECTED",
        body={"status": "GENERATING", "error_message": None},
        prefer="return=representation",
    ) or []
    return dict(updated[0]) if updated else None


def _claim_selected(limit: int = 2) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.SELECTED"
        "&select=id,idea_flow_id,idea,status,retry_count,content_package"
        f"&order=created_at.asc&limit={limit}",
    ) or []
    claimed: list[dict[str, Any]] = []
    for row in rows:
        job = _claim_selected_job(str(row["id"]))
        if job is not None:
            claimed.append(job)
    return claimed


def _finish_job(job: dict[str, Any], package: dict[str, Any],
                provider: str, model: str) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    existing_package = dict(job.get("content_package") or {})
    merged_package = {**existing_package, **package}
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
            "content_package": merged_package,
            "generator_provider": provider,
            "generator_model": model,
            "generator_version": GENERATOR_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "error_message": None,
        },
    )


def _fail_job(job: dict[str, Any], exc: Exception) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    retry_count = int(job.get("retry_count") or 0) + 1
    retryable = not isinstance(exc, NonRetryableGenerationError)
    status = "SELECTED" if retryable and retry_count <= 2 else "GENERATION_FAILED"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={
            "status": status,
            "retry_count": retry_count,
            "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
        },
    )


def _process_claimed_job(job: dict[str, Any]) -> bool:
    idea_id = job.get("idea_flow_id") or "?"
    try:
        package_context = dict(job.get("content_package") or {})
        targets = package_context.get("target_platforms") or []
        platform = (
            str(targets[0]).lower()
            if isinstance(targets, list) and targets
            else str(package_context.get("publish_platform") or "").lower()
        )
        feedback = feedback_for_candidate(
            platform=platform or None,
            content_format=str(package_context.get("format") or ""),
        )
        package_context["performance_feedback"] = feedback
        idea = str(job.get("idea") or "")
        result = _call_provider(
            idea,
            package_context,
        )
        if result is None:
            raise NonRetryableGenerationError(
                "No AI generation provider succeeded; refusing template fallback"
            )
        package, provider, model = result
        package["performance_feedback"] = feedback
        revenue_opportunity = _revenue_opportunity(package_context)
        if revenue_opportunity:
            package["revenue_opportunity"] = revenue_opportunity
        if _is_facebook_personal(package_context):
            package["voice_profile_id"] = "facebook_personal_voice_v1"
        package["semantic_fidelity"] = _enforce_semantic_fidelity(idea, package)
        _finish_job(job, package, provider, model)
        _send_telegram(
            f"✍️ Job #{idea_id} — READY_FOR_REVIEW\n"
            f"Hook: {package['hook']}\n\n"
            f"ใช้ /job {idea_id} เพื่อตรวจสถานะ"
        )
        return True
    except Exception as exc:
        print("content_generation_error", {
            "idea_flow_id": idea_id,
            "exception_type": type(exc).__name__,
        })
        _fail_job(job, exc)
        return False


def process_selected_job(job_id: str) -> bool:
    job = _claim_selected_job(job_id)
    return _process_claimed_job(job) if job is not None else False


def process_selected_once() -> int:
    return sum(1 for job in _claim_selected() if _process_claimed_job(job))


async def content_worker_loop() -> None:
    await asyncio.sleep(3)
    while True:
        try:
            await asyncio.to_thread(process_selected_once)
        except Exception as exc:
            print("content_worker_loop_error", {"exception_type": type(exc).__name__})
        await asyncio.sleep(30)
