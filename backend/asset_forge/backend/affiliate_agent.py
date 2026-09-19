"""Affiliate program discovery and deterministic opportunity analysis."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/affiliate", tags=["affiliate-agent"])

OPENAFFILIATE_BASE_URL = "https://openaffiliate.dev"
_USER_AGENT = "SoloForge-Affiliate-Agent/0.1"
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
