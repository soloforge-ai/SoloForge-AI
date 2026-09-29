"""Authenticated publishing actions for SoloForge mobile Content Ops."""

from __future__ import annotations

from datetime import datetime, timezone
import urllib.parse

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)

from backend.shared_supabase import supabase_request as _supabase_request

from backend.publora_publishing import (
    default_platform_ids,
    list_connections,
    publish_now_time,
    submit_to_publora,
)


router = APIRouter(prefix="/v1/publishing", tags=["publishing"])

_FIELDS = (
    "id,idea,status,caption,cta,script,publish_platform,publish_status,"
    "publora_post_id,published_at,video_storage_path,content_package,updated_at"
)


class PublishRequest(BaseModel):
    platform_ids: list[str] = Field(default_factory=list, max_length=10)


class ScheduleRequest(PublishRequest):
    scheduled_time: datetime


def _require_session(authorization: str | None) -> None:
    if not get_pollinations_access_token_from_authorization(authorization):
        raise HTTPException(status_code=401, detail="SoloForge session required")


def _get_job(job_id: str) -> dict[str, object]:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select={_FIELDS}&limit=1",
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])


def _finish_submission(
    job: dict[str, object],
    payload: dict[str, object],
    *,
    platform_ids: list[str],
    scheduled_time: datetime,
) -> dict[str, object]:
    post_group_id = str(payload.get("postGroupId") or "").strip()
    if not post_group_id:
        raise HTTPException(status_code=502, detail="Publora did not return a postGroupId")

    package = dict(job.get("content_package") or {})
    package.update(
        {
            "publish_platform_ids": platform_ids,
            "scheduled_time": scheduled_time.astimezone(timezone.utc).isoformat(),
        }
    )
    encoded = urllib.parse.quote(str(job["id"]), safe="")
    rows = _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{encoded}&status=eq.READY_TO_PUBLISH",
        body={
            "status": "PUBLISHING",
            "publish_status": "QUEUED",
            "publora_post_id": post_group_id,
            "content_package": package,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        prefer="return=representation",
    ) or []
    if not rows:
        raise HTTPException(status_code=409, detail="Content job changed before publishing")
    return dict(rows[0])


def _submit(
    job_id: str,
    platform_ids: list[str],
    scheduled_time: datetime,
) -> dict[str, object]:
    job = _get_job(job_id)
    if job.get("status") != "READY_TO_PUBLISH":
        raise HTTPException(
            status_code=409,
            detail="Only READY_TO_PUBLISH content can be published",
        )

    try:
        connections = list_connections()
        selected = platform_ids or default_platform_ids(job, connections)
        if not selected:
            raise ValueError(
                "No connected Publora account matches this content. Select a connected account."
            )
        payload = submit_to_publora(
            job,
            platform_ids=selected,
            scheduled_time=scheduled_time,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _finish_submission(
        job,
        payload,
        platform_ids=selected,
        scheduled_time=scheduled_time,
    )


@router.get("/connections")
def publishing_connections(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    try:
        rows = list_connections()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "items": [
            {
                "platformId": row.get("platformId"),
                "username": row.get("username"),
                "displayName": row.get("displayName"),
                "connectionStatus": row.get("connectionStatus"),
                "tokenStatus": row.get("tokenStatus"),
            }
            for row in rows
            if row.get("platformId")
        ]
    }


@router.post("/{job_id}/publish-now")
def publish_now(
    job_id: str,
    request: PublishRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    return _submit(job_id, request.platform_ids, publish_now_time())


@router.post("/{job_id}/schedule")
def schedule(
    job_id: str,
    request: ScheduleRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    scheduled_time = request.scheduled_time
    if scheduled_time.tzinfo is None:
        scheduled_time = scheduled_time.replace(tzinfo=timezone.utc)
    return _submit(job_id, request.platform_ids, scheduled_time)
