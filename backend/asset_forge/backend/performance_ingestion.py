from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import urllib.parse

from backend.publora_publishing import get_post, list_connections
from backend.shared_supabase import supabase_request as _supabase_request


_METRIC_FIELDS = (
    "views",
    "impressions",
    "reach",
    "reactions",
    "comments",
    "shares",
    "saves",
    "clicks",
    "watch_time_seconds",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def provider_capabilities() -> list[dict[str, Any]]:
    rows = []
    for connection in list_connections():
        platform_id = str(connection.get("platformId") or "")
        if not platform_id:
            continue
        platform = platform_id.split("-", 1)[0].strip().lower()
        rows.append(
            {
                "provider": "publora",
                "platform": platform,
                "platform_id": platform_id,
                "username": connection.get("username"),
                "connection_status": connection.get("connectionStatus"),
                "token_status": connection.get("tokenStatus"),
                "metadata_sync": True,
                "engagement_metrics": False
                if platform in {"instagram", "tiktok", "youtube"}
                else None,
            }
        )
    return rows


def _insert_event(
    job_id: str,
    *,
    event_type: str,
    actor: str,
    metadata: dict[str, Any],
) -> None:
    _supabase_request(
        "POST",
        "content_job_events",
        body={
            "content_job_id": job_id,
            "event_type": event_type,
            "actor": actor,
            "metadata": metadata,
            "occurred_at": _now(),
        },
    )


def sync_publora_metadata(job: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job.get("id") or "")
    post_group_id = str(job.get("publora_post_id") or "").strip()
    if not job_id:
        raise ValueError("Content job id is required")
    if not post_group_id:
        raise ValueError("Content job is not linked to a Publora post")

    payload = get_post(post_group_id)
    posts = payload.get("posts") or []

    platform_posts: list[dict[str, Any]] = []
    for raw in posts:
        if not isinstance(raw, dict):
            continue
        platform = str(raw.get("platform") or "").lower()
        platform_posts.append(
            {
                "platform": platform,
                "status": raw.get("status"),
                "platform_post_id": raw.get("postedId"),
                "permalink": raw.get("permalink"),
                "metrics_supported": False
                if platform in {"instagram", "tiktok", "youtube"}
                else None,
            }
        )

    result = {
        "provider": "publora",
        "post_group_id": post_group_id,
        "status": payload.get("status"),
        "platform_posts": platform_posts,
        "metrics_ingested": 0,
        "synced_at": _now(),
    }

    _insert_event(
        job_id,
        event_type="PROVIDER_SYNC",
        actor="publora",
        metadata=result,
    )
    return result


def store_import_snapshot(
    item: dict[str, Any],
) -> dict[str, Any]:
    job_id = str(item.get("content_job_id") or "").strip()
    if not job_id:
        raise ValueError("content_job_id is required")

    encoded = urllib.parse.quote(job_id, safe="")
    jobs = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&select=id,publora_post_id&limit=1",
    ) or []
    if not jobs:
        raise ValueError(f"Unknown content job: {job_id}")

    job = dict(jobs[0])
    body: dict[str, Any] = {
        "content_job_id": job_id,
        "platform": str(item.get("platform") or "").strip().lower(),
        "source": "import",
        "publora_post_id": item.get("publora_post_id") or job.get("publora_post_id"),
        "platform_post_id": item.get("platform_post_id"),
        "metadata": dict(item.get("metadata") or {}),
    }
    if not body["platform"]:
        raise ValueError("platform is required")

    for key in _METRIC_FIELDS:
        value = item.get(key)
        if value is not None:
            body[key] = value

    observed_at = item.get("observed_at")
    if observed_at:
        body["observed_at"] = observed_at

    rows = _supabase_request(
        "POST",
        "content_performance_snapshots",
        body=body,
        prefer="return=representation",
    ) or []
    if not rows:
        raise RuntimeError("Performance snapshot was not stored")
    return dict(rows[0])


def aggregate_latest_snapshots(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        key = (
            str(row.get("content_job_id") or ""),
            str(row.get("platform") or ""),
        )
        if key not in latest:
            latest[key] = row

    total_views = 0
    total_reactions = 0
    total_comments = 0
    total_shares = 0
    total_saves = 0
    total_clicks = 0

    for row in latest.values():
        total_views += int(row.get("views") or 0)
        total_reactions += int(row.get("reactions") or 0)
        total_comments += int(row.get("comments") or 0)
        total_shares += int(row.get("shares") or 0)
        total_saves += int(row.get("saves") or 0)
        total_clicks += int(row.get("clicks") or 0)

    interactions = (
        total_reactions
        + total_comments
        + total_shares
        + total_saves
        + total_clicks
    )
    engagement_rate = (
        round((interactions / total_views) * 100, 2)
        if total_views > 0
        else None
    )

    return {
        "latest_series": len(latest),
        "total_views": total_views,
        "total_reactions": total_reactions,
        "total_comments": total_comments,
        "total_shares": total_shares,
        "total_saves": total_saves,
        "total_clicks": total_clicks,
        "total_interactions": interactions,
        "engagement_rate_percent": engagement_rate,
    }
