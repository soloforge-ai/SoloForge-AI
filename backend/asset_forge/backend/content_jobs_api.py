from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Header, HTTPException, Query

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
    "publish_status,generator_provider,generator_model,generated_at,"
    "created_at,updated_at,content_package"
)


def _require_session(authorization: str | None) -> None:
    if not get_pollinations_access_token_from_authorization(authorization):
        raise HTTPException(status_code=401, detail="SoloForge session required")


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
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select={_FIELDS}&limit=1",
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])
