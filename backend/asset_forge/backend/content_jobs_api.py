from __future__ import annotations

from datetime import datetime, timezone
import urllib.parse
import uuid

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)
from backend.content_intake import find_recommendation, recommend_formats, score_idea
from backend.content_strategy import strategize_idea

from backend.shared_supabase import supabase_request as _supabase_request


router = APIRouter(prefix="/v1/content-jobs", tags=["content-jobs"])

_FIELDS = (
    "id,idea,status,score,score_reason,hook,script,caption,cta,"
    "visual_prompt,motion_prompt,risk_level,qa_status,publish_platform,"
    "publish_status,publora_post_id,published_at,video_storage_path,"
    "generator_provider,generator_model,generated_at,"
    "created_at,updated_at,content_package"
)

_EDITABLE_DRAFT_FIELDS = {
    "hook",
    "script",
    "caption",
    "cta",
    "visual_prompt",
    "motion_prompt",
}

_REGENERATE_FROM = {
    "BACKLOG",
    "READY_FOR_REVIEW",
    "GENERATION_FAILED",
    "SELECTED",
}

_GENERATED_PACKAGE_KEYS = {
    "hook",
    "script",
    "caption",
    "cta",
    "onscreen_text",
    "visual_prompt",
    "motion_prompt",
    "risk_level",
}


class IdeaAnalyzeRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=4000)


class IdeaCreateRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=4000)
    recommendation_id: str = Field(min_length=1, max_length=80)
    action: str = Field(default="generate", pattern="^(generate|save)$")


class IdeaStrategizeRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=4000)


class StrategyPlanCreateRequest(BaseModel):
    idea: str = Field(min_length=3, max_length=4000)
    plan_id: str = Field(pattern="^(quick_test|mini_series|seven_day)$")
    action: str = Field(default="generate", pattern="^(generate|save)$")


class ContentDraftUpdate(BaseModel):
    hook: str | None = Field(default=None, max_length=4000)
    script: str | None = Field(default=None, max_length=20000)
    caption: str | None = Field(default=None, max_length=10000)
    cta: str | None = Field(default=None, max_length=4000)
    visual_prompt: str | None = Field(default=None, max_length=20000)
    motion_prompt: str | None = Field(default=None, max_length=20000)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_session(authorization: str | None) -> None:
    if not get_pollinations_access_token_from_authorization(authorization):
        raise HTTPException(status_code=401, detail="SoloForge session required")


def _get_row(job_id: str) -> dict[str, object]:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select={_FIELDS}&limit=1",
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])


def _patch_job(job_id: str, body: dict[str, object]) -> dict[str, object]:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{encoded}",
        body=body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise HTTPException(status_code=409, detail="Content job update was not applied")
    return dict(rows[0])



@router.post("/idea/analyze")
def analyze_idea(request: IdeaAnalyzeRequest) -> dict[str, object]:
    return recommend_formats(request.idea)


@router.post("/idea/strategize")
def strategize_content_idea(
    request: IdeaStrategizeRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    return strategize_idea(request.idea)


@router.post("/idea/plan/create")
def create_strategy_plan(
    request: StrategyPlanCreateRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    strategy = strategize_idea(request.idea)
    plan = next(
        (item for item in strategy["plans"] if item["id"] == request.plan_id),
        None,
    )
    if plan is None:
        raise HTTPException(status_code=400, detail="Unknown strategy plan")

    campaign_id = str(uuid.uuid4())
    score = score_idea(request.idea)
    total = int(plan["job_count"])
    created: list[dict[str, object]] = []

    for raw_job in plan["jobs"]:
        sequence = int(raw_job["sequence"])
        dependencies = list(raw_job.get("depends_on") or [])
        blocked = bool(dependencies)
        status = (
            "SELECTED"
            if request.action == "generate" and not blocked
            else "BACKLOG"
        )
        fmt = str(raw_job.get("format") or "content")
        needs_video = any(
            token in fmt.lower()
            for token in ("video", "reel", "shorts", "short_video")
        )
        platforms = list(plan.get("platforms") or [])
        publish_platform = str(platforms[0]) if platforms else "tiktok"
        asset_requirements = list(raw_job.get("asset_requirements") or [])

        package = {
            "format": fmt,
            "goal": str(raw_job.get("goal") or plan.get("goal") or "reach"),
            "priority": "MEDIUM",
            "target_platforms": platforms,
            "needs_video": needs_video,
            "campaign_id": campaign_id,
            "campaign_plan_id": request.plan_id,
            "campaign_title": str(plan.get("title") or request.plan_id),
            "campaign_sequence": sequence,
            "campaign_total": total,
            "content_title": str(raw_job.get("title") or f"Content {sequence}"),
            "asset_requirements": asset_requirements,
            "depends_on": dependencies,
            "generation_brief": {
                "hook_direction": str(raw_job.get("hook_direction") or ""),
                "strategy_angle": str(strategy["strategy"].get("angle") or ""),
                "strategy_objective": str(strategy["strategy"].get("objective") or ""),
                "strategy_rationale": str(strategy["strategy"].get("rationale") or ""),
            },
            "strategy": {
                "strategist_version": strategy.get("strategist_version"),
                "strategist_provider": strategy.get("strategist_provider"),
                "strategist_model": strategy.get("strategist_model"),
                "recommended_plan_id": strategy["strategy"].get("recommended_plan_id"),
                "selected_plan_id": request.plan_id,
                "human_action": request.action,
            },
        }
        if blocked:
            package["blocker"] = (
                "Waiting for: " + ", ".join(str(item) for item in dependencies)
            )

        rows = _supabase_request(
            "POST",
            "content_jobs",
            body={
                "idea": (
                    f"{request.idea.strip()}\n\n"
                    f"Campaign {sequence}/{total}: {package['content_title']}"
                ),
                "source": "app_strategy_plan",
                "status": status,
                "score": score["score"],
                "score_reason": score["reason"],
                "score_breakdown": score["breakdown"],
                "score_version": score["version"],
                "scored_at": _now(),
                "publish_platform": publish_platform,
                "content_package": package,
                "qa_status": "PENDING",
                "updated_at": _now(),
            },
            prefer="return=representation",
        ) or []
        if not rows:
            raise HTTPException(
                status_code=500,
                detail=f"Campaign creation stopped at item {sequence}",
            )

        job = dict(rows[0])
        created.append(job)
        _supabase_request(
            "POST",
            "content_job_events",
            body={
                "content_job_id": job["id"],
                "event_type": "STRATEGY_PLAN_JOB_CREATED",
                "actor": "app",
                "metadata": {
                    "campaign_id": campaign_id,
                    "plan_id": request.plan_id,
                    "sequence": sequence,
                    "total": total,
                    "action": request.action,
                },
                "occurred_at": _now(),
            },
        )

    return {
        "campaign_id": campaign_id,
        "plan_id": request.plan_id,
        "plan_title": plan["title"],
        "created_count": len(created),
        "jobs": created,
    }


@router.post("/idea/create")
def create_from_idea(
    request: IdeaCreateRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    try:
        recommendation = find_recommendation(
            request.idea,
            request.recommendation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    score = score_idea(request.idea)
    next_status = "SELECTED" if request.action == "generate" else "BACKLOG"
    recommendation_set = recommend_formats(request.idea)
    package = {
        "format": recommendation["id"],
        "goal": recommendation["goal"],
        "priority": "MEDIUM",
        "target_platforms": recommendation["platforms"],
        "needs_video": recommendation["needs_video"],
        "generation_brief": {
            "hook_direction": recommendation["hook_direction"],
            "recommendation_reason": recommendation["reason"],
            "production_difficulty": recommendation["production_difficulty"],
        },
        "idea_composer": {
            "recommender_version": recommendation_set["recommender_version"],
            "recommended": recommendation["recommended"],
            "fit_score": recommendation["fit_score"],
            "human_action": request.action,
            "miniboss_original_decision": score["decision"],
            "human_override": request.action == "generate" and score["decision"] != "SELECTED",
        },
    }
    rows = _supabase_request(
        "POST",
        "content_jobs",
        body={
            "idea": request.idea.strip(),
            "source": "app_idea_composer",
            "status": next_status,
            "score": score["score"],
            "score_reason": score["reason"],
            "score_breakdown": score["breakdown"],
            "score_version": score["version"],
            "scored_at": _now(),
            "publish_platform": recommendation["platforms"][0],
            "content_package": package,
            "qa_status": "PENDING",
            "updated_at": _now(),
        },
        prefer="return=representation",
    ) or []
    if not rows:
        raise HTTPException(status_code=500, detail="Content job was not created")

    job = dict(rows[0])
    _supabase_request(
        "POST",
        "content_job_events",
        body={
            "content_job_id": job["id"],
            "event_type": "IDEA_COMPOSER_CREATED",
            "actor": "app",
            "metadata": {
                "format": recommendation["id"],
                "action": request.action,
                "fit_score": recommendation["fit_score"],
            },
            "occurred_at": _now(),
        },
    )
    return job


@router.get("")
def list_content_jobs(
    limit: int = Query(default=100, ge=1, le=200),
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    rows = _supabase_request(
        "GET",
        f"content_jobs?select={_FIELDS}&order=created_at.desc&limit={limit}",
    ) or []
    return {"items": rows}


@router.get("/{job_id}")
def get_content_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    return _get_row(job_id)


@router.patch("/{job_id}/draft")
def update_content_draft(
    job_id: str,
    request: ContentDraftUpdate,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    if current.get("status") not in {"READY_FOR_REVIEW", "BACKLOG"}:
        raise HTTPException(
            status_code=409,
            detail="Draft can only be edited while waiting for review or in backlog",
        )

    raw = request.model_dump(exclude_unset=True)
    body = {
        key: value
        for key, value in raw.items()
        if key in _EDITABLE_DRAFT_FIELDS
    }
    if not body:
        raise HTTPException(status_code=400, detail="No draft fields supplied")

    package = dict(current.get("content_package") or {})
    for key, value in body.items():
        package[key] = value

    body.update(
        {
            "content_package": package,
            "qa_status": "PENDING",
            "updated_at": _now(),
        }
    )
    return _patch_job(job_id, body)


@router.post("/{job_id}/approve")
def approve_content_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    if current.get("status") != "READY_FOR_REVIEW":
        raise HTTPException(
            status_code=409,
            detail="Only READY_FOR_REVIEW content can be approved",
        )
    now = _now()
    return _patch_job(
        job_id,
        {
            "status": "APPROVED",
            "qa_status": "PASS",
            "approved_at": now,
            "updated_at": now,
            "error_message": None,
        },
    )


@router.post("/{job_id}/regenerate")
def regenerate_content_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    status = str(current.get("status") or "")
    if status not in _REGENERATE_FROM:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot regenerate while status is {status}",
        )

    package = dict(current.get("content_package") or {})
    for key in _GENERATED_PACKAGE_KEYS:
        package.pop(key, None)

    return _patch_job(
        job_id,
        {
            "status": "SELECTED",
            "hook": None,
            "script": None,
            "caption": None,
            "cta": None,
            "visual_prompt": None,
            "motion_prompt": None,
            "qa_status": "PENDING",
            "content_package": package,
            "generator_provider": None,
            "generator_model": None,
            "generated_at": None,
            "error_message": None,
            "retry_count": 0,
            "updated_at": _now(),
        },
    )
