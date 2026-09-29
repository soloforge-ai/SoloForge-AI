"""Route approved content jobs into the minimum required production pipeline."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import urllib.parse
from typing import Any

from backend.shared_supabase import supabase_request as _supabase_request


ROUTER_VERSION = "content_router_v0.1"

_VIDEO_HINTS = ("video", "reel", "shorts", "short_video", "tiktok_video")
_VISUAL_HINTS = (
    "carousel",
    "breakdown",
    "image",
    "graphic",
    "infographic",
    "quote_card",
    "poster",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_route(content_package: dict[str, Any]) -> str:
    if content_package.get("needs_video") is True:
        return "VIDEO"

    fmt = str(content_package.get("format") or "").strip().lower()
    if any(token in fmt for token in _VIDEO_HINTS):
        return "VIDEO"
    if any(token in fmt for token in _VISUAL_HINTS):
        return "VISUAL"
    return "TEXT"


def _claim_approved(limit: int = 4) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.APPROVED"
        "&select=id,idea_flow_id,status,content_package"
        f"&order=updated_at.asc&limit={limit}",
    ) or []

    claimed: list[dict[str, Any]] = []
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        package = dict(row.get("content_package") or {})
        route = classify_route(package)
        package.update(
            {
                "pipeline_route": route,
                "router_version": ROUTER_VERSION,
                "routed_at": _now(),
            }
        )
        next_status = "READY_TO_PUBLISH" if route == "TEXT" else "ASSET_QUEUED"
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.APPROVED",
            body={
                "status": next_status,
                "content_package": package,
                "updated_at": _now(),
                "error_message": None,
            },
            prefer="return=representation",
        ) or []
        if updated:
            claimed.append(dict(updated[0]))
    return claimed


def process_approved_routes_once() -> int:
    return len(_claim_approved())


async def content_router_loop() -> None:
    await asyncio.sleep(4)
    while True:
        try:
            await asyncio.to_thread(process_approved_routes_once)
        except Exception as exc:
            print(
                "content_router_loop_error",
                {"exception_type": type(exc).__name__},
            )
        await asyncio.sleep(20)
