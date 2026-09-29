from __future__ import annotations

from datetime import datetime
import urllib.parse
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from backend.performance_ingestion import (
    aggregate_latest_snapshots,
    provider_capabilities,
    store_import_snapshot,
    sync_publora_metadata,
)
from backend.pollinations_oauth_router import (
    get_pollinations_access_token_from_authorization,
)
from backend.shared_supabase import supabase_request as _supabase_request


router = APIRouter(prefix="/v1/analytics", tags=["analytics"])

_ANALYTICS_FIELDS = (
    "id,status,score,publish_platform,publish_status,"
    "created_at,generated_at,approved_at,published_at"
)


class PerformanceSnapshotRequest(BaseModel):
    platform: str = Field(min_length=1, max_length=80)
    source: str = Field(default="manual", pattern="^(manual|publora|platform_api|import)$")
    publora_post_id: str | None = Field(default=None, max_length=500)
    platform_post_id: str | None = Field(default=None, max_length=1000)
    views: int | None = Field(default=None, ge=0)
    impressions: int | None = Field(default=None, ge=0)
    reach: int | None = Field(default=None, ge=0)
    reactions: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    clicks: int | None = Field(default=None, ge=0)
    watch_time_seconds: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PerformanceImportItem(PerformanceSnapshotRequest):
    content_job_id: str = Field(min_length=1, max_length=80)
    observed_at: datetime | None = None


class PerformanceImportRequest(BaseModel):
    items: list[PerformanceImportItem] = Field(min_length=1, max_length=100)


def _require_session(authorization: str | None) -> None:
    if not get_pollinations_access_token_from_authorization(authorization):
        raise HTTPException(status_code=401, detail="SoloForge session required")


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_seconds(start: object, end: object) -> float | None:
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)
    if start_dt is None or end_dt is None:
        return None
    return max(0.0, (end_dt - start_dt).total_seconds())


def _average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _require_job(job_id: str) -> dict[str, object]:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select=id,publora_post_id,publish_platform&limit=1",
    ) or []
    if not rows:
        raise HTTPException(status_code=404, detail="Content job not found")
    return dict(rows[0])


@router.get("/providers")
def analytics_providers(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    return {"items": provider_capabilities()}


@router.get("/summary")
def analytics_summary(
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    rows = _supabase_request(
        "GET",
        f"content_jobs?select={_ANALYTICS_FIELDS}&order=created_at.desc&limit=500",
    ) or []

    by_status: dict[str, int] = {}
    by_platform: dict[str, int] = {}
    scores: list[float] = []
    generation_seconds: list[float] = []
    publish_seconds: list[float] = []

    published = 0
    failed = 0
    review = 0

    for raw in rows:
        row = dict(raw)
        status = str(row.get("status") or "UNKNOWN")
        by_status[status] = by_status.get(status, 0) + 1

        platform = str(row.get("publish_platform") or "unknown")
        by_platform[platform] = by_platform.get(platform, 0) + 1

        if status == "PUBLISHED" or row.get("publish_status") == "PUBLISHED":
            published += 1
        if status.endswith("_FAILED"):
            failed += 1
        if status == "READY_FOR_REVIEW":
            review += 1

        score = row.get("score")
        if isinstance(score, (int, float)):
            scores.append(float(score))
        elif score is not None:
            try:
                scores.append(float(score))
            except (TypeError, ValueError):
                pass

        generation_duration = _duration_seconds(
            row.get("created_at"),
            row.get("generated_at"),
        )
        if generation_duration is not None:
            generation_seconds.append(generation_duration)

        publish_duration = _duration_seconds(
            row.get("created_at"),
            row.get("published_at"),
        )
        if publish_duration is not None:
            publish_seconds.append(publish_duration)

    performance_rows = _supabase_request(
        "GET",
        "content_performance_snapshots"
        "?select=id,content_job_id,platform,source,views,impressions,reach,"
        "reactions,comments,shares,saves,clicks,watch_time_seconds,observed_at"
        "&order=observed_at.desc&limit=500",
    ) or []
    performance = aggregate_latest_snapshots(
        [dict(row) for row in performance_rows]
    )

    return {
        "jobs_total": len(rows),
        "published": published,
        "failed": failed,
        "review": review,
        "average_score": _average(scores),
        "average_generation_seconds": _average(generation_seconds),
        "average_time_to_publish_seconds": _average(publish_seconds),
        "by_status": by_status,
        "by_platform": by_platform,
        "performance_snapshots": len(performance_rows),
        "performance_available": bool(performance_rows),
        **performance,
    }


@router.get("/jobs/{job_id}/timeline")
def job_timeline(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    _require_job(job_id)
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        "content_job_events"
        f"?content_job_id=eq.{encoded}"
        "&select=id,event_type,from_status,to_status,actor,metadata,occurred_at"
        "&order=occurred_at.asc",
    ) or []
    return {"items": rows}


@router.get("/jobs/{job_id}/performance")
def job_performance(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    _require_job(job_id)
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        "content_performance_snapshots"
        f"?content_job_id=eq.{encoded}"
        "&select=id,platform,publora_post_id,platform_post_id,source,views,"
        "impressions,reach,reactions,comments,shares,saves,clicks,"
        "watch_time_seconds,metadata,observed_at,created_at"
        "&order=observed_at.desc",
    ) or []
    return {"items": rows}


@router.post("/jobs/{job_id}/sync-provider")
def sync_job_provider(
    job_id: str,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    job = _require_job(job_id)
    try:
        return sync_publora_metadata(job)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/performance")
def add_performance_snapshot(
    job_id: str,
    request: PerformanceSnapshotRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    job = _require_job(job_id)
    body = request.model_dump()
    body["content_job_id"] = job_id
    if not body.get("publora_post_id"):
        body["publora_post_id"] = job.get("publora_post_id")

    rows = _supabase_request(
        "POST",
        "content_performance_snapshots",
        body=body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise HTTPException(status_code=409, detail="Performance snapshot was not stored")
    return dict(rows[0])


@router.post("/performance/import")
def import_performance(
    request: PerformanceImportRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    _require_session(authorization)
    stored: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for item in request.items:
        body = item.model_dump(mode="json")
        body["source"] = "import"
        try:
            stored.append(store_import_snapshot(body))
        except (ValueError, RuntimeError) as exc:
            errors.append(
                {
                    "content_job_id": item.content_job_id,
                    "error": str(exc),
                }
            )

    return {
        "stored": len(stored),
        "failed": len(errors),
        "errors": errors,
        "items": stored,
    }
