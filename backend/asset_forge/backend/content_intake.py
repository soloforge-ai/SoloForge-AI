from __future__ import annotations

import re
from typing import Any

MINIBOSS_SCORE_VERSION = "miniboss_v0_rule_boundaryfix1_feedback1"
RECOMMENDER_VERSION = "format_recommender_v0.1"


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _has_term(text: str, term: str) -> bool:
    term = term.lower()
    if re.fullmatch(r"[a-z0-9_ -]+", term):
        pattern = rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])"
        return re.search(pattern, text) is not None
    return term in text


def _has_any(text: str, *terms: str) -> bool:
    return any(_has_term(text, term) for term in terms)


def score_idea(idea: str) -> dict[str, object]:
    text = _normalize(idea)

    audience_fit = 12
    if _has_any(text, "ai", "เครื่องมือ", "แอป", "ทำงาน", "ครีเอเตอร์", "creator", "affiliate"):
        audience_fit += 5
    if _has_any(text, "ประหยัดเวลา", "รายได้", "เงิน", "productivity", "งาน"):
        audience_fit += 3
    audience_fit = min(audience_fit, 20)

    hook_potential = 10
    if _has_any(text, "ฟรี", "ทดลอง", "จริง", "คุ้ม", "ได้ไหม", "แทนมนุษย์", "ไม่ต้อง", "ทำไม"):
        hook_potential += 6
    if len(text) >= 35:
        hook_potential += 2
    if _has_any(text, "ai", "เครื่องมือ", "แอป"):
        hook_potential += 2
    hook_potential = min(hook_potential, 20)

    revenue_potential = 8
    if _has_any(text, "affiliate", "สินค้า", "product", "รายได้", "เงิน", "ขาย", "คอมมิชชั่น"):
        revenue_potential += 10
    if _has_any(text, "เครื่องมือ", "แอป", "tool", "software", "saas"):
        revenue_potential += 5
    if _has_any(text, "ฟรี", "ทดลอง"):
        revenue_potential += 2
    revenue_potential = min(revenue_potential, 25)

    trend_potential = 8
    if _has_any(text, "ai", "automation", "agent", "เครื่องมือ", "แอป"):
        trend_potential += 5
    if _has_any(text, "ทดลอง", "รีวิว", "เทียบ", "จริง"):
        trend_potential += 2
    trend_potential = min(trend_potential, 15)

    brand_fit = 6
    if _has_any(text, "ai", "เครื่องมือ", "แอป", "automation"):
        brand_fit += 2
    if _has_any(text, "ทดลอง", "ใช้จริง", "รายได้", "affiliate", "ประหยัดเวลา"):
        brand_fit += 2
    brand_fit = min(brand_fit, 10)

    production_ease = 7
    if _has_any(text, "เครื่องมือ", "แอป", "เว็บ", "website", "tool", "ai"):
        production_ease += 2
    if _has_any(text, "ทดลอง", "รีวิว", "สอน", "วิธี", "เทียบ"):
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


def recommend_formats(idea: str) -> dict[str, Any]:
    text = _normalize(idea)
    demo_signal = _has_any(
        text,
        "ลอง", "ทดลอง", "รีวิว", "เทียบ", "before", "after",
        "ก่อนใช้", "หลังใช้", "ก่อนทำ", "หลังทำ",
        "ทำไม", "ปัญหา", "พัง", "ไม่เหมือน", "เปลี่ยน",
    )
    educational_signal = _has_any(
        text,
        "วิธี", "สอน", "ขั้นตอน", "เหตุผล", "ทำไม", "how", "why", "แก้", "เทคนิค",
    )
    personal_signal = _has_any(
        text,
        "เรา", "เคย", "เมื่อก่อน", "ตอนนั้น", "ประสบการณ์", "รู้สึก", "เจอ",
    )
    discussion_signal = _has_any(
        text,
        "ไหม", "หรือเปล่า", "คิดว่า", "เคยไหม", "ใคร", "แบบไหน",
    )
    sales_signal = _has_any(
        text,
        "ขาย", "สินค้า", "affiliate", "คอมมิชชั่น", "โปร", "โปรโมชั่น",
        "โปรโมท", "โปรโมต", "promotion", "promo", "ราคา", "ซื้อ", "ebook",
        "e-book", "หนังสือ", "ลิงก์", "link", "http://", "https://",
    )

    scores = {
        "short_video_demo": 54
        + (28 if demo_signal else 0)
        + (4 if sales_signal else 0),
        "carousel": 52
        + (20 if educational_signal else 0)
        + (5 if demo_signal else 0),
        "personal_post": 50
        + (30 if personal_signal else 0),
        "question_post": 46
        + (22 if discussion_signal else 0),
        "promo_post": 48
        + (36 if sales_signal else 0),
    }

    specs = {
        "short_video_demo": {
            "title": "Short Video Demo",
            "platforms": ["tiktok", "instagram", "youtube"],
            "goal": "reach",
            "needs_video": True,
            "hook_direction": "เปิดด้วยปัญหาหรือผลลัพธ์ที่เห็นทันที แล้วสาธิตให้ดู",
            "production_difficulty": "MEDIUM",
            "reason": "เหมาะกับเรื่องที่มีการทดลอง ปัญหา หรือ Before/After ให้เห็นภาพเร็ว",
        },
        "carousel": {
            "title": "Carousel",
            "platforms": ["instagram", "facebook"],
            "goal": "education",
            "needs_video": False,
            "hook_direction": "เปิดด้วยข้อผิดพลาดหรือคำถาม แล้วแตกเป็นขั้นตอนสั้น ๆ",
            "production_difficulty": "LOW",
            "reason": "เหมาะกับการอธิบายเหตุผล วิธีแก้ หรือหลายประเด็นแบบอ่านง่าย",
        },
        "personal_post": {
            "title": "Personal Post",
            "platforms": ["facebook", "threads"],
            "goal": "connection",
            "needs_video": False,
            "hook_direction": "เปิดจากประสบการณ์จริงหรือความคิดที่คนอ่านเอาตัวเองไปแทนได้",
            "production_difficulty": "LOW",
            "reason": "เหมาะกับไอเดียที่มีมุมประสบการณ์ ความเห็น หรือเรื่องเล่าส่วนตัว",
        },
        "question_post": {
            "title": "Question Post",
            "platforms": ["facebook", "threads"],
            "goal": "engagement",
            "needs_video": False,
            "hook_direction": "เปลี่ยนแก่นของไอเดียเป็นคำถามสั้นที่ชวนตอบจากประสบการณ์",
            "production_difficulty": "LOW",
            "reason": "เหมาะกับการเปิดบทสนทนาและเก็บสัญญาณว่าคนสนใจประเด็นนี้แค่ไหน",
        },
        "promo_post": {
            "title": "Promo / Sales Post",
            "platforms": ["instagram", "facebook"],
            "goal": "conversion",
            "needs_video": False,
            "hook_direction": "เปิดด้วยประโยชน์หรือผลลัพธ์ที่คนจะได้ แล้วค่อยพาไปที่สินค้าและคำชวนทำต่อ",
            "production_difficulty": "LOW",
            "reason": "เหมาะกับไอเดียที่ตั้งใจโปรโมตสินค้า ebook ลิงก์ หรือข้อเสนอเพื่อให้เกิดการคลิกหรือซื้อ",
        },
    }

    candidate_keys = [
        "short_video_demo",
        "carousel",
        "personal_post",
        "question_post",
    ]
    if sales_signal:
        candidate_keys.append("promo_post")

    ranked = sorted(candidate_keys, key=lambda key: scores[key], reverse=True)[:4]
    options: list[dict[str, Any]] = []
    for index, key in enumerate(ranked):
        spec = specs[key]
        options.append(
            {
                "id": key,
                "title": spec["title"],
                "rank": index + 1,
                "fit_score": min(int(scores[key]), 99),
                "recommended": index == 0,
                "platforms": spec["platforms"],
                "goal": spec["goal"],
                "needs_video": spec["needs_video"],
                "hook_direction": spec["hook_direction"],
                "production_difficulty": spec["production_difficulty"],
                "reason": spec["reason"],
            }
        )

    return {
        "idea": idea.strip(),
        "recommender_version": RECOMMENDER_VERSION,
        "recommended_format": ranked[0],
        "options": options,
        "miniboss": score_idea(idea),
    }


def find_recommendation(idea: str, recommendation_id: str) -> dict[str, Any]:
    result = recommend_formats(idea)
    for option in result["options"]:
        if option["id"] == recommendation_id:
            return dict(option)
    raise ValueError("Unknown recommendation format")
