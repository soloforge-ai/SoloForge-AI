"""Generate the first publishable visual asset for routed SoloForge content jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.asset_provider import generate_asset
from backend.shared_supabase import supabase_request as _supabase_request


ASSET_BUCKET = "content-assets"
ASSET_WORKER_VERSION = "content_asset_v0.1"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_assets(limit: int = 2) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.ASSET_QUEUED"
        "&select=id,idea_flow_id,idea,visual_prompt,retry_count,content_package"
        f"&order=updated_at.asc&limit={limit}",
    ) or []

    claimed: list[dict[str, Any]] = []
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        package = dict(row.get("content_package") or {})
        package.update(
            {
                "asset_status": "GENERATING",
                "asset_worker_version": ASSET_WORKER_VERSION,
            }
        )
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.ASSET_QUEUED",
            body={
                "status": "ASSET_GENERATING",
                "content_package": package,
                "error_message": None,
                "updated_at": _now(),
            },
            prefer="return=representation",
        ) or []
        if updated:
            claimed.append(dict(updated[0]))
    return claimed


def _upload_asset(data: bytes, object_path: str) -> None:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    request = urllib.request.Request(
        f"{base_url}/storage/v1/object/{ASSET_BUCKET}/{encoded_path}",
        data=data,
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "image/png",
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response.read()
    except Exception as exc:
        raise RuntimeError("Asset upload failed") from exc


def _finish_asset(job: dict[str, Any], object_path: str, provider_meta: dict[str, object]) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    package = dict(job.get("content_package") or {})
    route = str(package.get("pipeline_route") or "VISUAL")
    package.update(
        {
            "asset_status": "READY",
            "asset_storage_path": object_path,
            "asset_generated_at": _now(),
            "asset_count": 1,
            "asset_mode": "cover_v1",
            "asset_worker_version": ASSET_WORKER_VERSION,
            "asset_provider": provider_meta.get("provider"),
            "asset_mode": provider_meta.get("mode") or "cover_v1",
            "asset_provider_version": provider_meta.get("provider_version"),
            "asset_provider_attempts": provider_meta.get("attempts") or [],
        }
    )

    next_status = "ASSET_READY" if route == "VIDEO" else "READY_TO_PUBLISH"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}&status=eq.ASSET_GENERATING",
        body={
            "status": next_status,
            "content_package": package,
            "qa_status": "PASS",
            "error_message": None,
            "updated_at": _now(),
        },
    )


def _fail_asset(job: dict[str, Any], exc: Exception) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    retry_count = int(job.get("retry_count") or 0) + 1
    retry = retry_count <= 2
    package = dict(job.get("content_package") or {})
    package["asset_status"] = "PENDING" if retry else "FAILED"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={
            "status": "ASSET_QUEUED" if retry else "ASSET_FAILED",
            "content_package": package,
            "retry_count": retry_count,
            "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
            "updated_at": _now(),
        },
    )


def process_assets_once() -> int:
    processed = 0
    for job in _claim_assets():
        try:
            prompt = str(job.get("visual_prompt") or "").strip()
            if not prompt:
                prompt = (
                    "Editorial social media visual, clean premium creator-tech design, "
                    f"topic: {str(job.get('idea') or '')[:400]}"
                )
            package = dict(job.get("content_package") or {})
            data, provider_meta = generate_asset(
                prompt,
                fallback_title=str(job.get("idea") or "SoloForge")[:240],
                fallback_subtitle=str(package.get("goal") or "").strip() or None,
            )
            object_path = f"{job['id']}/cover.png"
            _upload_asset(data, object_path)
            _finish_asset(job, object_path, provider_meta)
            processed += 1
        except Exception as exc:
            print(
                "content_asset_error",
                {
                    "idea_flow_id": job.get("idea_flow_id"),
                    "exception_type": type(exc).__name__,
                },
            )
            _fail_asset(job, exc)
    return processed


async def content_asset_worker_loop() -> None:
    await asyncio.sleep(6)
    while True:
        try:
            await asyncio.to_thread(process_assets_once)
        except Exception as exc:
            print(
                "content_asset_worker_loop_error",
                {"exception_type": type(exc).__name__},
            )
        await asyncio.sleep(30)
