from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from backend.content_intake import recommend_formats, score_idea


STRATEGIST_VERSION = "content_strategist_v0.1"

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

SYSTEM_PROMPT = """You are SoloForge Content Strategist for the Ai HackWork brand.
Turn one rough Thai content idea into an actionable content strategy and exactly 3 selectable production plans.
Return ONLY one JSON object.

Required keys:
strategy, plans

strategy keys:
angle, objective, audience, rationale, missing_inputs, recommended_plan_id

Each plan must contain:
id, title, summary, job_count, goal, platforms, asset_requirements, jobs

Each job must contain:
sequence, title, format, goal, hook_direction, asset_requirements, depends_on

Rules:
- plans must use these ids exactly: quick_test, mini_series, seven_day
- quick_test has 1 job
- mini_series has 3 jobs
- seven_day has 7 jobs
- Do not invent sales, views, clicks, product facts, personal experience, prices, or results.
- If a later job requires real results, make that dependency explicit, for example performance_after_publish.
- Treat missing product photos, screenshots, links, references, or proof as missing inputs, not facts.
- Prefer practical content that can actually be produced.
- Reply in Thai for human-facing text. Technical ids and format names stay in English.
"""


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fence = chr(96) * 3
    if cleaned.startswith(fence):
        cleaned = cleaned.replace(f"{fence}json", "", 1).replace(fence, "").strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Strategist did not return JSON")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Strategist response must be an object")
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
            "temperature": 0.25,
            "max_tokens": 3200,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if provider == "openrouter":
            headers["X-OpenRouter-Title"] = "SoloForge Content Strategist"
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=75) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return _extract_json(content), provider, model
        except Exception as exc:
            print("content_strategist_provider_error", {
                "provider": provider,
                "exception_type": type(exc).__name__,
            })
    return None


def _job(
    sequence: int,
    title: str,
    fmt: str,
    goal: str,
    hook_direction: str,
    assets: list[str],
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "title": title,
        "format": fmt,
        "goal": goal,
        "hook_direction": hook_direction,
        "asset_requirements": assets,
        "depends_on": depends_on or [],
    }


def _fallback_strategy(idea: str) -> dict[str, Any]:
    recommendation = recommend_formats(idea)
    text = idea.lower()
    experiment = any(term in text for term in ("ลอง", "ทดลอง", "รีวิว", "จริงไหม", "คุ้มไหม"))
    sales = any(term in text for term in ("ขาย", "สินค้า", "digital product", "ebook", "e-book", "โปรโมต", "โปรโมท"))
    personal = any(term in text for term in ("เรา", "เคย", "ประสบการณ์"))

    if experiment and sales:
        angle = "Build in Public / Experiment"
        objective = "พาคนดูตามการทดลองตั้งแต่เริ่มทำ จนเห็นสิ่งที่ทำจริงและผลลัพธ์จริง"
        rationale = "ไอเดียมีทั้งการทดลองและการขาย จึงเหมาะกับการเล่าเป็นเส้นทางที่พิสูจน์ได้ทีละขั้น"
    elif experiment:
        angle = "Experiment / Proof"
        objective = "ทดลองโจทย์ให้เห็นกระบวนการ ข้อจำกัด และข้อสรุปจากหลักฐานจริง"
        rationale = "ไอเดียมีภาษาของการทดลอง จึงควรเน้นสิ่งที่ทำจริงแทนการสรุปล่วงหน้า"
    elif sales:
        angle = "Problem → Product → Proof"
        objective = "อธิบายปัญหา คุณค่าของสินค้า และพาไปสู่การตัดสินใจโดยไม่แต่งผลลัพธ์"
        rationale = "ไอเดียมีเจตนาขาย จึงควรแยกการให้คุณค่ากับ CTA ให้ชัด"
    elif personal:
        angle = "Personal Story → Lesson"
        objective = "ใช้ประสบการณ์เป็นแกน แล้วสรุปบทเรียนที่คนอ่านเอาไปใช้ต่อได้"
        rationale = "ไอเดียมีมุมประสบการณ์ส่วนตัว จึงเหมาะกับ narrative ที่เชื่อมกับคนอ่าน"
    else:
        angle = "Teach / Demonstrate"
        objective = "เปลี่ยนไอเดียให้เป็นตัวอย่างที่เข้าใจง่ายและมีขั้นตอนทำตามได้"
        rationale = "ยังไม่มีสัญญาณแคมเปญเฉพาะ จึงเริ่มจากรูปแบบที่พิสูจน์คุณค่าได้เร็ว"

    primary = recommendation["options"][0]
    primary_format = str(primary["id"])
    platforms = list(primary["platforms"])

    common_missing = ["ภาพหรือหลักฐานจริงที่เกี่ยวข้องกับเนื้อหา"]
    if sales:
        common_missing.extend(["ภาพสินค้า/หน้าปก", "ลิงก์สินค้าหรือหน้าร้าน"])
    if experiment:
        common_missing.append("หลักฐานผลการทดลองจริงเมื่อมีข้อมูล")

    quick_jobs = [
        _job(
            1,
            "เปิดโจทย์และทดลองหนึ่งชิ้น",
            primary_format,
            str(primary["goal"]),
            str(primary["hook_direction"]),
            common_missing[:2],
        )
    ]

    mini_jobs = [
        _job(1, "ทำไมถึงลองเรื่องนี้", "personal_post" if personal else primary_format, "reach",
             "เปิดด้วยเหตุผลที่ทำให้ตัดสินใจลอง และสิ่งที่ต้องการพิสูจน์", common_missing[:2]),
        _job(2, "เบื้องหลังและขั้นตอนจริง", "carousel", "education",
             "แยกขั้นตอน สิ่งที่ AI ช่วยได้ และสิ่งที่ยังต้องทำเอง", ["ภาพขั้นตอน", "screenshot ที่ไม่เปิดเผยข้อมูลลับ"]),
        _job(3, "สรุปสิ่งที่ได้จากการลอง", primary_format, "engagement",
             "สรุปจากหลักฐานจริงว่าอะไรเวิร์ก อะไรไม่เวิร์ก และควรทำต่อไหม", ["ผลลัพธ์จริง"], ["performance_after_publish"]),
    ]

    seven_jobs = [
        _job(1, "เริ่มต้นการทดลอง", primary_format, "reach",
             "เปิดโจทย์ว่าได้ยินอะไรมาและกำลังจะพิสูจน์อะไร", common_missing[:2]),
        _job(2, "เลือกสิ่งที่จะทำ", "carousel", "education",
             "อธิบายเกณฑ์เลือกสินค้า/หัวข้อโดยไม่ทำให้ดูเป็นสูตรสำเร็จ", ["ภาพตัวอย่างหรือ reference"]),
        _job(3, "ใช้ AI ช่วยตรงไหน", "short_video_demo", "education",
             "โชว์ขั้นตอนที่ AI ช่วยจริงและส่วนที่ต้องตรวจเอง", ["screenshot workflow"]),
        _job(4, "ของที่ทำออกมาจริง", "carousel", "proof",
             "โชว์ชิ้นงานจริง พร้อมข้อดีและข้อจำกัด", ["product image", "product preview"]),
        _job(5, "เตรียมขายหรือเผยแพร่", "promo_post" if sales else primary_format, "conversion" if sales else "reach",
             "พาไปดูวิธีจัดหน้าขาย/เผยแพร่และ CTA ที่ตรงกับสิ่งที่มีจริง", ["store/listing screenshot", "product link"] if sales else ["publish screenshot"]),
        _job(6, "ผลตอบรับระหว่างทาง", "personal_post", "proof",
             "รายงานเฉพาะข้อมูลจริงที่เกิดขึ้น เช่น views, clicks, saves, sales หรือสิ่งที่เรียนรู้", ["performance data"], ["performance_after_publish"]),
        _job(7, "สรุป 7 วัน", "short_video_demo", "retention",
             "สรุปสิ่งที่ได้เรียนรู้ สิ่งที่จะทำต่อ และสิ่งที่ไม่ควรทำซ้ำ", ["recap assets", "performance data"], ["performance_after_publish"]),
    ]

    return {
        "strategy": {
            "angle": angle,
            "objective": objective,
            "audience": "คนที่สนใจใช้ AI เพื่อทำงาน สร้างคอนเทนต์ หรือสร้างรายได้อย่างลงมือทำจริง",
            "rationale": rationale,
            "missing_inputs": common_missing,
            "recommended_plan_id": "mini_series" if experiment else "quick_test",
        },
        "plans": [
            {
                "id": "quick_test",
                "title": "Quick Test",
                "summary": "ทำ 1 ชิ้นเพื่อทดสอบมุมและความสนใจก่อนขยาย",
                "job_count": 1,
                "goal": str(primary["goal"]),
                "platforms": platforms,
                "asset_requirements": common_missing[:2],
                "jobs": quick_jobs,
            },
            {
                "id": "mini_series",
                "title": "Mini Series 3 ตอน",
                "summary": "เล่าโจทย์ → ขั้นตอน → สิ่งที่ได้จากการทดลอง",
                "job_count": 3,
                "goal": "validation",
                "platforms": platforms,
                "asset_requirements": common_missing,
                "jobs": mini_jobs,
            },
            {
                "id": "seven_day",
                "title": "7-Day Campaign",
                "summary": "ทำเป็น Build in Public 7 วัน ตั้งแต่เริ่มจนสรุปผล",
                "job_count": 7,
                "goal": "campaign",
                "platforms": platforms,
                "asset_requirements": common_missing,
                "jobs": seven_jobs,
            },
        ],
    }


def _normalize_strategy(raw: dict[str, Any], idea: str) -> dict[str, Any]:
    fallback = _fallback_strategy(idea)
    strategy = raw.get("strategy") if isinstance(raw.get("strategy"), dict) else {}
    raw_plans = raw.get("plans") if isinstance(raw.get("plans"), list) else []

    expected_counts = {"quick_test": 1, "mini_series": 3, "seven_day": 7}
    normalized_plans: list[dict[str, Any]] = []
    fallback_by_id = {p["id"]: p for p in fallback["plans"]}

    for plan_id in ("quick_test", "mini_series", "seven_day"):
        source = next(
            (p for p in raw_plans if isinstance(p, dict) and p.get("id") == plan_id),
            None,
        )
        fb = fallback_by_id[plan_id]
        if source is None:
            normalized_plans.append(fb)
            continue

        jobs = source.get("jobs") if isinstance(source.get("jobs"), list) else []
        if len(jobs) != expected_counts[plan_id]:
            normalized_plans.append(fb)
            continue

        normalized_jobs = []
        for idx, row in enumerate(jobs, start=1):
            if not isinstance(row, dict):
                normalized_jobs = list(fb["jobs"])
                break
            normalized_jobs.append({
                "sequence": idx,
                "title": str(row.get("title") or f"Content {idx}").strip(),
                "format": str(row.get("format") or fb["jobs"][min(idx - 1, len(fb["jobs"]) - 1)]["format"]).strip(),
                "goal": str(row.get("goal") or "reach").strip(),
                "hook_direction": str(row.get("hook_direction") or "").strip(),
                "asset_requirements": _normalize_list(row.get("asset_requirements")),
                "depends_on": _normalize_list(row.get("depends_on")),
            })

        normalized_plans.append({
            "id": plan_id,
            "title": str(source.get("title") or fb["title"]).strip(),
            "summary": str(source.get("summary") or fb["summary"]).strip(),
            "job_count": expected_counts[plan_id],
            "goal": str(source.get("goal") or fb["goal"]).strip(),
            "platforms": _normalize_list(source.get("platforms")) or list(fb["platforms"]),
            "asset_requirements": _normalize_list(source.get("asset_requirements")) or list(fb["asset_requirements"]),
            "jobs": normalized_jobs,
        })

    recommended = str(strategy.get("recommended_plan_id") or fallback["strategy"]["recommended_plan_id"])
    if recommended not in expected_counts:
        recommended = fallback["strategy"]["recommended_plan_id"]

    return {
        "idea": idea.strip(),
        "strategist_version": STRATEGIST_VERSION,
        "strategy": {
            "angle": str(strategy.get("angle") or fallback["strategy"]["angle"]).strip(),
            "objective": str(strategy.get("objective") or fallback["strategy"]["objective"]).strip(),
            "audience": str(strategy.get("audience") or fallback["strategy"]["audience"]).strip(),
            "rationale": str(strategy.get("rationale") or fallback["strategy"]["rationale"]).strip(),
            "missing_inputs": _normalize_list(strategy.get("missing_inputs")) or list(fallback["strategy"]["missing_inputs"]),
            "recommended_plan_id": recommended,
        },
        "plans": normalized_plans,
        "miniboss": score_idea(idea),
    }


def strategize_idea(idea: str) -> dict[str, Any]:
    result = _call_provider(idea)
    if result is None:
        normalized = _normalize_strategy(_fallback_strategy(idea), idea)
        normalized["strategist_provider"] = "deterministic_fallback"
        normalized["strategist_model"] = "v0"
        return normalized

    raw, provider, model = result
    normalized = _normalize_strategy(raw, idea)
    normalized["strategist_provider"] = provider
    normalized["strategist_model"] = model
    return normalized


def find_plan(idea: str, plan_id: str) -> dict[str, Any]:
    result = strategize_idea(idea)
    for plan in result["plans"]:
        if plan["id"] == plan_id:
            return dict(plan)
    raise ValueError("Unknown strategy plan")
