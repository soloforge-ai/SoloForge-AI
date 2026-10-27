from __future__ import annotations

from backend.execution_policy import require_generation_execution

from datetime import datetime, timezone
import json
from typing import Literal
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.soloforge_session import require_soloforge_session
from backend.content_intake import find_recommendation, recommend_formats, score_idea
from backend.content_generation import process_selected_job
from backend.content_router import route_approved_job
from backend.content_asset_generation import process_asset_job
from backend.asset_provider import requires_ceo_asset_review, require_ceo_render_provenance
from backend.audio_generation import process_video_asset_job
from backend.final_render import process_audio_ready_job
from backend.publora_publishing import media_urls_for_job, _signed_storage_url
from backend.content_job_skill_adapter import preview_content_job_skill
from backend.product_grounding import (
    ProductGroundingError,
    is_commercial_product_job,
    validate_product_grounding,
)
from backend.product_resolver import ProductResolverError, resolve_shopee_product

from backend.shared_supabase import supabase_request as _supabase_request


router = APIRouter(prefix="/v1/content-jobs", tags=["content-jobs"])

_FIELDS = (
    "id,idea,status,score,score_reason,hook,script,caption,cta,"
    "visual_prompt,motion_prompt,risk_level,qa_status,publish_platform,"
    "publish_status,publora_post_id,published_at,video_storage_path,render_status,render_qa,video_url,"
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


class ProductGroundingUpdate(BaseModel):
    canonical_title: str = Field(min_length=1, max_length=1000)
    image_urls: list[str] = Field(min_length=1, max_length=12)
    source: str = Field(default="manual", min_length=1, max_length=80)
    shop_name: str | None = Field(default=None, max_length=500)
    price: str | float | int | None = None
    product_url: str | None = Field(default=None, max_length=4000)
    affiliate_url: str | None = Field(default=None, max_length=4000)


class ProductResolveRequest(BaseModel):
    url: str = Field(min_length=8, max_length=4000)


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
    if not rows or (rows[0].get("content_package") or {}).get("byop_principal"):
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])


def _continue_approved_job(job_id: str) -> None:
    require_generation_execution()
    routed = route_approved_job(job_id)
    if not routed or routed.get("status") != "ASSET_QUEUED":
        return

    if not process_asset_job(job_id):
        return
    if not process_video_asset_job(job_id):
        return
    process_audio_ready_job(job_id)


def _resume_job(job_id: str, status: str) -> None:
    require_generation_execution()
    if status == "APPROVED":
        _continue_approved_job(job_id)
        return

    if status == "ASSET_QUEUED":
        if not process_asset_job(job_id):
            return
        if not process_video_asset_job(job_id):
            return
        process_audio_ready_job(job_id)
        return

    if status == "ASSET_READY":
        if not process_video_asset_job(job_id):
            return
        process_audio_ready_job(job_id)
        return

    if status == "AUDIO_READY":
        process_audio_ready_job(job_id)


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


@router.post("/idea/create")
def create_from_idea(
    request: IdeaCreateRequest,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    if request.action == "generate":
        require_generation_execution()
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
        f"content_jobs?select={_FIELDS}&content_package->>byop_principal=is.null&order=created_at.desc&limit={limit}",
    ) or []
    return {"items": rows}


@router.get("/{job_id}")
def get_content_job(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    return _get_row(job_id)


@router.get("/{job_id}/skill-preview")
def get_skill_preview(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Dry-run an existing queued job through the Content Skill adapter/runtime."""
    _require_session(authorization)
    return preview_content_job_skill(_get_row(job_id))


@router.get("/{job_id}/asset-preview")
def get_asset_preview(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    job = _get_row(job_id)
    package = dict(job.get("content_package") or {})
    route = str(package.get("pipeline_route") or "").strip().upper()

    ceo_preview = requires_ceo_asset_review(package) and package.get("asset_status") == "READY"
    if ceo_preview:
        path = str(package.get("asset_storage_path") or "").strip()
        digest = str(package.get("asset_sha256") or "")
        if not path or len(digest) != 64:
            raise HTTPException(409, "CEO image has no verifiable preview")
        urls = [_signed_storage_url("content-assets", path)]
    else:
        urls = media_urls_for_job(job)
    if not urls:
        raise HTTPException(status_code=404, detail="No generated asset is available")

    return {
        "url": urls[0],
        "media_type": "image" if ceo_preview else ("video" if route == "VIDEO" else "image"),
        "asset_status": package.get("asset_status"),
        "pipeline_route": route or None,
        **({"asset_sha256": digest} if ceo_preview else {}),
    }


@router.post("/{job_id}/resolve-product")
def resolve_product_for_job(
    job_id: str,
    request: ProductResolveRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Resolve a Shopee URL and attach validated product grounding to a draft job."""
    _require_session(authorization)
    current = _get_row(job_id)
    if current.get("status") not in {"BACKLOG", "READY_FOR_REVIEW"}:
        raise HTTPException(
            status_code=409,
            detail="Product can only be resolved before approval",
        )

    try:
        resolution = resolve_shopee_product(request.url)
        grounding = validate_product_grounding(
            {"product_grounding": resolution["grounding"]}
        )
    except (ProductResolverError, ProductGroundingError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    package = dict(current.get("content_package") or {})
    package["product_grounding"] = grounding
    package["product_grounding_status"] = "READY"
    package["product_resolution"] = {
        "resolver_version": resolution["resolver_version"],
        "provider": resolution["provider"],
        "input_url": resolution["input_url"],
        "resolved_url": resolution["resolved_url"],
    }
    package.pop("product_grounding_error", None)

    return _patch_job(
        job_id,
        {
            "content_package": package,
            "qa_status": "PENDING",
            "updated_at": _now(),
        },
    )


@router.patch("/{job_id}/product-grounding")
def update_product_grounding(
    job_id: str,
    request: ProductGroundingUpdate,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    """Attach and lock verified product identity before commercial asset generation."""
    _require_session(authorization)
    current = _get_row(job_id)
    if current.get("status") not in {"BACKLOG", "READY_FOR_REVIEW"}:
        raise HTTPException(
            status_code=409,
            detail="Product grounding can only be changed before approval",
        )

    package = dict(current.get("content_package") or {})
    package["product_grounding"] = request.model_dump(exclude_none=True)
    try:
        package["product_grounding"] = validate_product_grounding(package)
    except ProductGroundingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    package["product_grounding_status"] = "READY"
    package.pop("product_grounding_error", None)
    return _patch_job(
        job_id,
        {
            "content_package": package,
            "qa_status": "PENDING",
            "updated_at": _now(),
        },
    )


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


class AssetReviewRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    asset_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.post("/{job_id}/asset-review")
def review_content_asset(
    job_id: str,
    request: AssetReviewRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    package = dict(current.get("content_package") or {})
    if (
        current.get("status") != "READY_FOR_REVIEW"
        or not requires_ceo_asset_review(package)
        or package.get("asset_status") != "READY"
        or not package.get("asset_storage_path")
        or package.get("asset_sha256") != request.asset_sha256
    ):
        raise HTTPException(409, "Current CEO image is not available for this review")
    # Compare the full package so concurrent replacement/review cannot approve
    # a different image or overwrite another decision.
    previous = urllib.parse.quote(json.dumps(package, separators=(",", ":")), safe="")
    approved = request.decision == "APPROVED"
    semantic = package.get("semantic_fidelity")
    if approved and isinstance(semantic, dict) and str(semantic.get("status") or "").upper() in {"FAIL", "STALE"}:
        raise HTTPException(409, "Content must pass semantic fidelity before asset approval")
    package.update({"asset_review_status": request.decision,
                    "asset_review_sha256": request.asset_sha256 if approved else None,
                    "asset_reviewed_at": _now()})
    next_status = "READY_FOR_REVIEW"
    if approved:
        if package.get("pipeline_route") == "VIDEO" and current.get("video_url"):
            raise HTTPException(409, "CEO review rejects existing video_url; regenerate from the approved image")
        if package.get("pipeline_route") == "VIDEO" and current.get("video_storage_path"):
            try:
                require_ceo_render_provenance({**current, "content_package": package})
            except ValueError as exc:
                raise HTTPException(409, str(exc)) from exc
        needs_render = package.get("pipeline_route") == "VIDEO" and not (
            current.get("video_storage_path") and current.get("render_status") == "READY"
        )
        next_status = "ASSET_READY" if needs_render else "READY_TO_PUBLISH"
    rows = _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{urllib.parse.quote(job_id, safe='')}&status=eq.READY_FOR_REVIEW"
        f"&content_package=eq.{previous}",
        body={"status": next_status, "content_package": package,
              "qa_status": "PASS" if approved else "FAIL", "updated_at": _now()},
        prefer="return=representation",
    ) or []
    if not rows:
        raise HTTPException(409, "Content job changed before asset review")
    return dict(rows[0])


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
    if requires_ceo_asset_review(package) and package.get("asset_storage_path"):
        raise HTTPException(409, "Use asset-review to approve the current CEO image")
    if is_commercial_product_job(package):
        try:
            package["product_grounding"] = validate_product_grounding(package)
        except ProductGroundingError as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Commercial content requires product grounding before approval: {exc}",
            ) from exc

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
    require_generation_execution()
    now = _now()
    approved = _patch_job(
        job_id,
        {
            "status": "APPROVED",
            "qa_status": "PASS",
            "approved_at": now,
            "updated_at": now,
            "error_message": None,
            "content_package": package,
        },
    )
    background_tasks.add_task(_continue_approved_job, job_id)
    return approved


@router.post("/{job_id}/continue")
def continue_content_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    current = _get_row(job_id)
    status = str(current.get("status") or "")
    if status not in {"APPROVED", "ASSET_QUEUED", "ASSET_READY", "AUDIO_READY"}:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot continue while status is {status}",
        )

    package = dict(current.get("content_package") or {})
    route = str(package.get("pipeline_route") or "").strip().upper()
    if status != "APPROVED" and route != "VIDEO":
        raise HTTPException(
            status_code=409,
            detail="Continue is only supported for routed VIDEO jobs",
        )

    require_generation_execution()
    background_tasks.add_task(_resume_job, job_id, status)
    return current


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

    require_generation_execution()
    package = dict(current.get("content_package") or {})
    for key in _GENERATED_PACKAGE_KEYS:
        package.pop(key, None)
    ceo_asset = requires_ceo_asset_review(package)
    if ceo_asset:
        package["ceo_identity_required"] = True
        # A new content revision cannot inherit approval or reuse an old image.
        for key in (
            "asset_storage_path", "asset_sha256", "asset_review_sha256",
            "asset_review_status", "asset_reviewed_at", "asset_forge_manifest",
            "asset_status", "asset_generated_at", "asset_count",
        ):
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
            **({"video_storage_path": None, "render_status": None, "render_qa": None, "video_url": None}
               if ceo_asset else {}),
            "updated_at": _now(),
        },
    )
    background_tasks.add_task(process_selected_job, job_id)
    return selected
