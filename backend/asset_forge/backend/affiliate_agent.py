"""Affiliate program discovery and deterministic opportunity analysis."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)

router = APIRouter(prefix="/v1/affiliate", tags=["affiliate-agent"])

OPENAFFILIATE_BASE_URL = "https://openaffiliate.dev"
POLLINATIONS_CHAT_URL = "https://gen.pollinations.ai/v1/chat/completions"
_USER_AGENT = "SoloForge-Affiliate-Agent/0.2"
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#-]{1,}", re.IGNORECASE)


class AnalyzeRequest(BaseModel):
    niche: str = Field(default="", max_length=200)
    audience: str = Field(default="", max_length=500)


class OpportunityScore(BaseModel):
    audience_fit: float
    content_potential: float
    commission_score: float
    product_value: float
    competition: float
    total_score: float
    rationale: list[str]
    risks: list[str]
    content_angles: list[str]


class ContentGenerateRequest(BaseModel):
    slug: str = Field(min_length=1, max_length=160)
    platform: str = Field(default="youtube_shorts", min_length=1, max_length=80)
    format: str = Field(default="review", min_length=1, max_length=80)
    intent: str = Field(default="commercial_investigation", min_length=1, max_length=80)
    goal: str = Field(default="affiliate_click", min_length=1, max_length=80)
    niche: str = Field(default="AI Creator Tools", max_length=200)
    audience: str = Field(default="AI creators and beginners", max_length=500)
    language: str = Field(default="th", max_length=20)
    affiliate_url: str | None = Field(default=None, max_length=2000)


def _openaffiliate_get(path: str, query: dict[str, object] | None = None) -> Any:
    url = f"{OPENAFFILIATE_BASE_URL}{path}"
    if query:
        clean = {
            key: str(value).lower() if isinstance(value, bool) else str(value)
            for key, value in query.items()
            if value is not None and str(value).strip() != ""
        }
        if clean:
            url = f"{url}?{urllib.parse.urlencode(clean)}"

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(status_code=404, detail="Affiliate program not found.") from exc
        raise HTTPException(
            status_code=502,
            detail=f"OpenAffiliate request failed ({exc.code}).",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=504,
            detail="OpenAffiliate did not respond in time.",
        ) from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAffiliate returned an invalid response.",
        ) from exc


def _first(raw: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in raw and raw[name] is not None:
            return raw[name]
    return default


def _number(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _normalize_program(raw: dict[str, Any]) -> dict[str, Any]:
    commission = raw.get("commission")
    if not isinstance(commission, dict):
        commission = {}

    agents = raw.get("agents")
    if not isinstance(agents, dict):
        agents = {}

    payout = raw.get("payout")
    if not isinstance(payout, dict):
        payout = {}

    cookie_days = _first(raw, "cookie_days", "cookieDays")
    try:
        cookie_days = int(cookie_days) if cookie_days is not None else None
    except (TypeError, ValueError):
        cookie_days = None

    commission_type = _first(
        commission,
        "type",
        default=_first(raw, "commission_type", "commissionType"),
    )
    commission_rate = _first(
        commission,
        "rate",
        default=_first(raw, "commission_rate", "commissionRate"),
    )
    commission_value = _first(
        commission,
        "value",
        default=_first(raw, "commission_value", "commissionValue"),
    )

    slug = str(_first(raw, "slug", "id", default="")).strip()
    name = str(_first(raw, "name", "title", default=slug)).strip()

    return {
        "slug": slug,
        "name": name,
        "website": _first(raw, "url", "website"),
        "category": _first(raw, "category"),
        "short_description": _first(raw, "short_description", "shortDescription"),
        "description": _first(raw, "description"),
        "tags": list(raw.get("tags") or []),
        "commission": {
            "type": commission_type,
            "rate": commission_rate,
            "value": commission_value,
            "mode": commission.get("mode"),
            "currency": commission.get("currency"),
            "duration": commission.get("duration"),
            "conditions": commission.get("conditions"),
        },
        "cookie_days": cookie_days,
        "verified": bool(raw.get("verified") is True),
        "signup_url": _first(raw, "signup_url", "signupUrl"),
        "approval": _first(raw, "approval"),
        "approval_time": _first(raw, "approval_time", "approvalTime"),
        "restrictions": _first(raw, "restrictions"),
        "network": _first(raw, "network"),
        "marketing_materials": bool(raw.get("marketing_materials") is True),
        "api_available": bool(raw.get("api_available") is True),
        "free_trial": raw.get("free_trial") if isinstance(raw.get("free_trial"), bool) else None,
        "payout": {
            "minimum": payout.get("minimum"),
            "currency": payout.get("currency"),
            "frequency": payout.get("frequency"),
            "methods": list(payout.get("methods") or []),
        },
        "agents": {
            "prompt": agents.get("prompt"),
            "keywords": list(agents.get("keywords") or []),
            "use_cases": list(agents.get("use_cases") or []),
        },
        "last_verified_at": _first(raw, "last_verified_at", "lastVerifiedAt"),
        "updated_at": _first(raw, "updated_at", "updatedAt"),
        "source": "openaffiliate",
    }


def _program_list(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("programs"), list):
        rows = payload["programs"]
    elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
        rows = payload["data"]
    else:
        raise HTTPException(
            status_code=502,
            detail="OpenAffiliate returned an unsupported program-list response.",
        )
    return [_normalize_program(row) for row in rows if isinstance(row, dict)]


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(text or "") if len(token) > 1}


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _score_program(program: dict[str, Any], request: AnalyzeRequest) -> OpportunityScore:
    user_tokens = _tokens(f"{request.niche} {request.audience}")
    program_tokens = _tokens(
        " ".join(
            [
                str(program.get("name") or ""),
                str(program.get("category") or ""),
                str(program.get("short_description") or ""),
                str(program.get("description") or ""),
                " ".join(str(x) for x in program.get("tags") or []),
                " ".join(str(x) for x in (program.get("agents") or {}).get("keywords") or []),
                " ".join(str(x) for x in (program.get("agents") or {}).get("use_cases") or []),
            ]
        )
    )
    overlap = user_tokens & program_tokens
    if user_tokens:
        overlap_ratio = len(overlap) / max(1, min(len(user_tokens), 10))
        audience_fit = 35 + overlap_ratio * 65
    else:
        audience_fit = 50

    use_cases = (program.get("agents") or {}).get("use_cases") or []
    keywords = (program.get("agents") or {}).get("keywords") or []
    content_potential = 45
    content_potential += min(len(use_cases), 4) * 8
    content_potential += min(len(keywords), 6) * 3
    if program.get("description"):
        content_potential += 7

    commission = program.get("commission") or {}
    commission_type = str(commission.get("type") or "").lower()
    rate_num = _number(commission.get("value"))
    if rate_num is None:
        rate_num = _number(commission.get("rate"))
    commission_score = 25
    if "recurr" in commission_type:
        commission_score += 30
    elif commission_type:
        commission_score += 10
    if rate_num is not None:
        commission_score += min(rate_num, 50) * 0.7
    cookie_days = program.get("cookie_days")
    if isinstance(cookie_days, int):
        commission_score += min(cookie_days, 90) / 90 * 10

    product_value = 40
    if program.get("verified"):
        product_value += 20
    if program.get("marketing_materials"):
        product_value += 10
    if program.get("api_available"):
        product_value += 5
    if program.get("description"):
        product_value += 10
    if program.get("free_trial") is True:
        product_value += 10

    # V0.1 has no defensible external competition dataset yet.
    # Keep this neutral rather than hallucinating a market-competition score.
    competition = 50.0

    audience_fit = _clamp(audience_fit)
    content_potential = _clamp(content_potential)
    commission_score = _clamp(commission_score)
    product_value = _clamp(product_value)

    total = _clamp(
        audience_fit * 0.30
        + content_potential * 0.25
        + commission_score * 0.20
        + product_value * 0.15
        + competition * 0.10
    )

    rationale: list[str] = []
    if overlap:
        rationale.append(
            "Audience match keywords: " + ", ".join(sorted(overlap)[:8]) + "."
        )
    if "recurr" in commission_type:
        rationale.append("Recurring commission improves repeat-revenue potential.")
    if isinstance(cookie_days, int):
        rationale.append(f"Cookie window: {cookie_days} days.")
    if program.get("verified"):
        rationale.append("Registry entry is marked verified by OpenAffiliate.")
    if use_cases:
        rationale.append("Structured use cases provide multiple content angles.")
    if not rationale:
        rationale.append("Insufficient structured signals; score uses conservative defaults.")

    risks: list[str] = []
    if not program.get("verified"):
        risks.append("Registry entry is not verified; confirm terms on the official program page.")
    if program.get("restrictions"):
        risks.append(f"Restrictions: {program['restrictions']}")
    if rate_num is None:
        risks.append("Commission value is not numeric/published; verify before promotion.")
    risks.append("Competition score is neutral in V0.1 because no external competition dataset is connected.")

    angles: list[str] = []
    name = program.get("name") or "this tool"
    if use_cases:
        for case in use_cases[:3]:
            angles.append(f"How to use {name} for {case}")
    angles.extend(
        [
            f"{name}: hands-on review after real use",
            f"{name} tutorial for beginners",
            f"{name} vs alternatives: which workflow fits whom?",
        ]
    )

    return OpportunityScore(
        audience_fit=audience_fit,
        content_potential=content_potential,
        commission_score=commission_score,
        product_value=product_value,
        competition=competition,
        total_score=total,
        rationale=rationale,
        risks=risks,
        content_angles=angles[:6],
    )


def _extract_chat_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("chat response is not an object")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("chat response has no choices")
    first = choices[0]
    if not isinstance(first, dict):
        raise ValueError("chat choice is invalid")
    message = first.get("message")
    if not isinstance(message, dict):
        raise ValueError("chat choice has no message")
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        text = "".join(parts).strip()
        if text:
            return text
    raise ValueError("chat message content is empty")


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(stripped[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("content response is not an object")
    return payload


def _normalize_content_package(
    payload: dict[str, Any],
    program: dict[str, Any],
    request: ContentGenerateRequest,
    model: str,
) -> dict[str, Any]:
    def text_value(name: str, default: str = "") -> str:
        value = payload.get(name)
        return str(value).strip() if value is not None else default

    def string_list(name: str, limit: int) -> list[str]:
        value = payload.get(name)
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:limit]

    raw_claims = payload.get("claims")
    claims: list[dict[str, str]] = []
    if isinstance(raw_claims, list):
        for item in raw_claims[:12]:
            if not isinstance(item, dict):
                continue
            claim_type = str(item.get("claim_type") or "product_claim").strip()
            if claim_type not in {
                "sourced_fact",
                "product_claim",
                "first_hand_claim",
                "measured_result",
            }:
                claim_type = "product_claim"
            claim_text = str(item.get("claim_text") or "").strip()
            if not claim_text:
                continue
            evidence_required = str(item.get("evidence_required") or "").strip()
            if claim_type in {"first_hand_claim", "measured_result"} and not evidence_required:
                evidence_required = "Real hands-on test evidence is required before publishing this claim."
            claims.append(
                {
                    "claim_text": claim_text,
                    "claim_type": claim_type,
                    "evidence_required": evidence_required,
                    "verification_status": "unverified",
                }
            )

    affiliate_url = request.affiliate_url or program.get("signup_url") or program.get("website")
    disclosure = text_value(
        "affiliate_disclosure",
        "โพสต์นี้อาจมีลิงก์ Affiliate ซึ่งผู้จัดทำอาจได้รับค่าคอมมิชชันโดยไม่มีค่าใช้จ่ายเพิ่มสำหรับผู้ซื้อ",
    )

    tools = [
        {
            "tool_name": f"Pollinations ({model})",
            "role": "Script / Content Draft",
            "used_in_final_output": True,
        }
    ]

    return {
        "program_slug": program.get("slug"),
        "program_name": program.get("name"),
        "platform": request.platform,
        "format": request.format,
        "intent": request.intent,
        "goal": request.goal,
        "title": text_value("title", f"{program.get('name', 'Tool')} — review"),
        "hooks": string_list("hooks", 5),
        "script": text_value("script"),
        "shot_list": string_list("shot_list", 12),
        "voiceover": text_value("voiceover"),
        "visual_prompts": string_list("visual_prompts", 12),
        "thumbnail_brief": text_value("thumbnail_brief"),
        "cta": text_value("cta"),
        "description": text_value("description"),
        "affiliate_disclosure": disclosure,
        "affiliate_url": affiliate_url,
        "claims": claims,
        "tools": tools,
        "end_card": {
            "heading": "เบื้องหลังคลิปนี้",
            "items": [
                {
                    "role": "Script",
                    "tool": f"Pollinations ({model})",
                }
            ],
            "closing": "ทดลองจริง ใช้จริง แล้วค่อยเล่า",
        },
    }


def _generate_content_package(
    program: dict[str, Any],
    request: ContentGenerateRequest,
    access_token: str,
) -> dict[str, Any]:
    model = os.getenv("POLLINATIONS_TEXT_MODEL", "openai").strip() or "openai"
    source = {
        "name": program.get("name"),
        "category": program.get("category"),
        "description": program.get("description") or program.get("short_description"),
        "commission": program.get("commission"),
        "cookie_days": program.get("cookie_days"),
        "verified_registry_entry": program.get("verified"),
        "restrictions": program.get("restrictions"),
        "agents": program.get("agents"),
        "website": program.get("website"),
    }
    language_instruction = (
        "Write natural Thai suitable for a Thai creator audience."
        if request.language.lower().startswith("th")
        else f"Write in language code {request.language}."
    )

    system_prompt = """You are the SoloForge Affiliate Content Factory.
Create a practical content package from the supplied affiliate-program data.
Return ONLY one valid JSON object. No markdown fences.

Hard rules:
- Never pretend the creator personally tested, bought, earned from, or measured the product unless the prompt contains real evidence.
- If a proposed line would require first-hand testing or measurement, put it in claims with claim_type first_hand_claim or measured_result and keep the script phrased as a test/question, not as a proven result.
- Do not invent commission, cookie duration, pricing, restrictions, customer counts, ratings, revenue, or product capabilities.
- Registry data is a lead, not a guarantee. Encourage verification of important commercial terms.
- Do not promise income.
- Keep the content useful even if the viewer never buys.
- The CTA may invite the viewer to check the disclosed affiliate link, but must not use deceptive urgency.
- visual_prompts describe visuals only; do not claim they already exist.
- Keep hooks strong but non-misleading.

JSON schema:
{
  "title": "string",
  "hooks": ["string", "string", "string"],
  "script": "string",
  "shot_list": ["string"],
  "voiceover": "string",
  "visual_prompts": ["string"],
  "thumbnail_brief": "string",
  "cta": "string",
  "description": "string",
  "affiliate_disclosure": "string",
  "claims": [
    {
      "claim_text": "string",
      "claim_type": "sourced_fact|product_claim|first_hand_claim|measured_result",
      "evidence_required": "string"
    }
  ]
}"""

    user_prompt = f"""Create one content package.

Program data:
{json.dumps(source, ensure_ascii=False)}

Creator context:
- niche: {request.niche}
- audience: {request.audience}
- platform: {request.platform}
- format: {request.format}
- intent: {request.intent}
- goal: {request.goal}
- affiliate link available: {"yes" if request.affiliate_url else "not yet"}

{language_instruction}

For review/tutorial content, frame untested experiences as what the creator should test on camera.
Aim for a concise piece that can be produced with AI-assisted visuals plus screen recordings if needed."""

    upstream_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    upstream_request = urllib.request.Request(
        POLLINATIONS_CHAT_URL,
        data=json.dumps(upstream_payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(upstream_request, timeout=120) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Content AI request failed upstream ({exc.code}).",
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(
            status_code=504,
            detail="Content AI did not respond in time.",
        ) from exc

    try:
        upstream = json.loads(raw.decode("utf-8"))
        text = _extract_chat_text(upstream)
        payload = _parse_json_object(text)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Content AI returned an invalid structured response.",
        ) from exc

    return _normalize_content_package(payload, program, request, model)


def _get_program(slug: str) -> dict[str, Any]:
    safe_slug = urllib.parse.quote(slug.strip(), safe="")
    payload = _openaffiliate_get(f"/api/programs/{safe_slug}")
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=502,
            detail="OpenAffiliate returned an unsupported program response.",
        )
    return _normalize_program(payload)


@router.get("/programs")
def list_programs(
    q: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=100),
    commission_type: str | None = Query(default=None, alias="type", max_length=40),
    verified: bool | None = None,
    min_cookie_days: int | None = Query(default=None, ge=0, le=3650),
    free_trial: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict[str, Any]]:
    payload = _openaffiliate_get(
        "/api/programs",
        {
            "q": q,
            "category": category,
            "type": commission_type,
            "verified": verified,
        },
    )
    programs = _program_list(payload)

    if min_cookie_days is not None:
        programs = [
            p for p in programs
            if isinstance(p.get("cookie_days"), int)
            and p["cookie_days"] >= min_cookie_days
        ]
    if free_trial is not None:
        programs = [p for p in programs if p.get("free_trial") is free_trial]

    return programs[:limit]


@router.get("/programs/{slug}")
def get_program(slug: str) -> dict[str, Any]:
    return _get_program(slug)


@router.post("/programs/{slug}/analyze", response_model=OpportunityScore)
def analyze_program(slug: str, request: AnalyzeRequest) -> OpportunityScore:
    return _score_program(_get_program(slug), request)


@router.post("/content/generate")
def generate_content(
    request: ContentGenerateRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    access_token = get_pollinations_access_token_from_authorization(authorization)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Connect Pollinations before generating Affiliate content.",
        )
    program = _get_program(request.slug)
    return _generate_content_package(program, request, access_token)
