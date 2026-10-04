from __future__ import annotations

from datetime import datetime, timezone
import urllib.parse
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.soloforge_session import require_soloforge_session
from backend.content_intake import find_recommendation, recommend_formats, score_idea
from backend.content_generation import process_selected_job
from backend.content_router import route_approved_job
from backend.content_asset_generation import process_asset_job
from backend.publora_publishing import media_urls_for_job
from backend.publora_publishing import get_post

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


class ContentDraftUpdate(BaseModel):
    hook: str | None = Field(default=None, max_length=4000)
    script: str | None = Field(default=None, max_length=20000)
    caption: str | None = Field(default=None, max_length=10000)
    cta: str | None = Field(default=None, max_length=4000)
    visual_prompt: str | None = Field(default=None, max_length=20000)
    motion_prompt: str | None = Field(default=None, max_length=20000)


class QueueResetRequest(BaseModel):
    confirmation: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_session(authorization: str | None) -> None:
    require_soloforge_session(authorization)


def _get_row(job_id: str) -> dict[str, object]:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select={_FIELDS}&limit=1",
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])


def _continue_approved_job(job_id: str) -> None:
    routed = route_approved_job(job_id)
    if routed and routed.get("status") == "ASSET_QUEUED":
        process_asset_job(job_id)


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


def _require_cancel_owner(authorization: str | None) -> None:
    # The queue reset boundary deliberately returns 403 for anonymous and
    # authenticated non-owners alike; possession of a Supabase bearer is not
    # sufficient to authorize a Content Factory mutation.
    try:
        _require_session(authorization)
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            raise HTTPException(status_code=403, detail="Owner session required") from exc
        raise


def _cancel_jobs(job_id: str | None) -> dict[str, object]:
    if job_id is not None:
        try:
            job_id = str(UUID(job_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid job ID") from exc
    result = _supabase_request(
        "POST", "rpc/cancel_content_jobs", body={"p_job_id": job_id}
    )
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Queue cancellation did not return a result")
    if job_id is not None and result.get("selected") == 0:
        raise HTTPException(status_code=404, detail="Content job not found")
    # External lookup is read-only. A PUBLISHING row is never changed by the
    # cancellation transaction; even a Publora draft requires reconciliation.
    for skipped in result.get("skipped", []):
        if skipped.get("reason") != "EXTERNAL_RECONCILIATION_REQUIRED":
            continue
        post_id = skipped.pop("publora_post_id", None)
        if not post_id:
            skipped["external_state"] = "UNKNOWN_NO_REFERENCE"
            continue
        try:
            payload = get_post(str(post_id))
            skipped["external_state"] = str(payload.get("status") or "UNKNOWN")
        except RuntimeError:
            skipped["external_state"] = "UNAVAILABLE"
    if job_id is not None and result.get("skipped"):
        raise HTTPException(status_code=409, detail=result["skipped"][0])
    return result


@router.post("/queue/reset")
def reset_content_queue(
    request: QueueResetRequest | None = Body(default=None),
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_cancel_owner(authorization)
    if request is None or request.confirmation != "CANCEL ALL ACTIVE JOBS":
        raise HTTPException(status_code=400, detail="Explicit queue reset confirmation required")
    return _cancel_jobs(None)


@router.post("/{job_id}/cancel")
def cancel_content_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_cancel_owner(authorization)
    return _cancel_jobs(job_id)



@router.post("/idea/analyze")
def analyze_idea(request: IdeaAnalyzeRequest) -> dict[str, object]:
    return recommend_formats(request.idea)


@router.post("/idea/create")
def create_from_idea(
    request: IdeaCreateRequest,
    background_tasks: BackgroundTasks,
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
    if request.action == "generate":
        background_tasks.add_task(process_selected_job, str(job["id"]))
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


@router.get("/{job_id}/asset-preview")
def get_asset_preview(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    job = _get_row(job_id)
    package = dict(job.get("content_package") or {})
    route = str(package.get("pipeline_route") or "").strip().upper()

    urls = media_urls_for_job(job)
    if not urls:
        raise HTTPException(status_code=404, detail="No generated asset is available")

    return {
        "url": urls[0],
        "media_type": "video" if route == "VIDEO" else "image",
        "asset_status": package.get("asset_status"),
        "pipeline_route": route or None,
    }


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

    semantic = package.get("semantic_fidelity")
    if isinstance(semantic, dict):
        semantic = dict(semantic)
        semantic.update(
            {
                "status": "STALE",
                "reason": (
                    "Draft changed after AI generation. Regenerate before approval "
                    "so semantic fidelity can be checked again."
                ),
                "stale_at": _now(),
            }
        )
        package["semantic_fidelity"] = semantic

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
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    if current.get("status") != "READY_FOR_REVIEW":
        raise HTTPException(
            status_code=409,
            detail="Only READY_FOR_REVIEW content can be approved",
        )

    package = dict(current.get("content_package") or {})
    semantic = package.get("semantic_fidelity")
    if isinstance(semantic, dict):
        semantic_status = str(semantic.get("status") or "").strip().upper()
        if semantic_status in {"FAIL", "STALE"}:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Content must pass semantic fidelity before approval. "
                    "Regenerate the draft and review it again."
                ),
            )
    now = _now()
    approved = _patch_job(
        job_id,
        {
            "status": "APPROVED",
            "qa_status": "PASS",
            "approved_at": now,
            "updated_at": now,
            "error_message": None,
        },
    )
    background_tasks.add_task(_continue_approved_job, job_id)
    return approved


@router.post("/{job_id}/regenerate")
def regenerate_content_job(
    job_id: str,
    background_tasks: BackgroundTasks,
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

    selected = _patch_job(
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
    background_tasks.add_task(process_selected_job, job_id)
    return selected
