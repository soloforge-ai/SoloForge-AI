from __future__ import annotations

from datetime import datetime, timezone
import urllib.parse

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)

try:
    from backend.idea_flow_webhook import _supabase_request
except ImportError:
    from backend.asset_forge.backend.idea_flow_webhook import _supabase_request


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
