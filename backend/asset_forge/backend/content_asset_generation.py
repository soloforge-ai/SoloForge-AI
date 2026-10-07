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
from backend.branding import stamp_image_bytes
from backend.product_grounding import (
    ProductGroundingError,
    download_grounded_product_image,
    is_commercial_product_job,
    validate_product_grounding,
)
from backend.shared_supabase import supabase_request as _supabase_request


ASSET_BUCKET = "content-assets"
ASSET_WORKER_VERSION = "content_asset_v0.2"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claim_asset_job(job_id: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded}&status=eq.ASSET_QUEUED"
        "&select=id,idea_flow_id,idea,visual_prompt,retry_count,content_package"
        "&limit=1",
    ) or []
    if not rows:
        return None

    row = dict(rows[0])
    package = dict(row.get("content_package") or {})
    package.update(
        {
            "asset_status": "GENERATING",
            "asset_worker_version": ASSET_WORKER_VERSION,
        }
    )
    updated = _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{encoded}&status=eq.ASSET_QUEUED",
        body={
            "status": "ASSET_GENERATING",
            "content_package": package,
            "error_message": None,
            "updated_at": _now(),
        },
        prefer="return=representation",
    ) or []
    return dict(updated[0]) if updated else None


def _claim_assets(limit: int = 2) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.ASSET_QUEUED"
        "&select=id"
        f"&order=updated_at.asc&limit={limit}",
    ) or []

    claimed: list[dict[str, Any]] = []
    for row in rows:
        job = _claim_asset_job(str(row["id"]))
        if job is not None:
            claimed.append(job)
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
    except ProductGroundingError as exc:
        package = dict(job.get("content_package") or {})
        package["product_grounding_status"] = "BLOCKED"
        package["product_grounding_error"] = str(exc)
        job["content_package"] = package
        _fail_asset(job, exc)
        return False
    except Exception as exc:
        raise RuntimeError("Asset upload failed") from exc


def _video_asset_is_publishable(provider_meta: dict[str, object]) -> bool:
    mode = str(provider_meta.get("mode") or "").strip().lower()
    provider = str(provider_meta.get("provider") or "").strip().lower()
    return (
        (mode == "ai_generated" and provider != "local_template")
        or (mode == "product_grounded" and provider == "product_source")
    )


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
            "asset_layout": "cover_v1",
            "asset_worker_version": ASSET_WORKER_VERSION,
            "asset_provider": provider_meta.get("provider"),
            "asset_mode": provider_meta.get("mode") or "cover_v1",
            "asset_provider_version": provider_meta.get("provider_version"),
            "asset_provider_attempts": provider_meta.get("attempts") or [],
            "brand_applied": provider_meta.get("brand_applied") is True,
            "brand_text": provider_meta.get("brand_text"),
            "brand_stamp_version": provider_meta.get("brand_stamp_version"),
            "brand_position": provider_meta.get("brand_position"),
        }
    )

    if route == "VIDEO" and not _video_asset_is_publishable(provider_meta):
        package["asset_status"] = "FAILED"
        package["asset_quality_gate"] = {
            "result": "FAIL",
            "reason": (
                "VIDEO jobs require a real generated visual. "
                "Local text-template fallback is not publishable."
            ),
        }
        _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.ASSET_GENERATING",
            body={
                "status": "ASSET_FAILED",
                "content_package": package,
                "qa_status": "FAIL",
                "error_message": (
                    "Video visual generation fell back to local_template; "
                    "final render was blocked to prevent a text-card video."
                ),
                "updated_at": _now(),
            },
        )
        return

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


def _process_claimed_asset(job: dict[str, Any]) -> bool:
    try:
        package = dict(job.get("content_package") or {})
        if is_commercial_product_job(package):
            grounding = validate_product_grounding(package)
            data, provider_meta = download_grounded_product_image(
                str(grounding["image_urls"][0])
            )
            package["product_grounding"] = grounding
            job["content_package"] = package
            provider_meta["product_identity_status"] = grounding["identity_status"]
            provider_meta["product_title"] = grounding["canonical_title"]
        else:
            prompt = str(job.get("visual_prompt") or "").strip()
            if not prompt:
                prompt = (
                    "Editorial social media visual, clean premium creator-tech design, "
                    f"topic: {str(job.get('idea') or '')[:400]}"
                )
            data, provider_meta = generate_asset(
                prompt,
                fallback_title=str(job.get("idea") or "SoloForge")[:240],
                fallback_subtitle=str(package.get("goal") or "").strip() or None,
            )
        data, brand_meta = stamp_image_bytes(data)
        provider_meta = {**provider_meta, **brand_meta}
        object_path = f"{job['id']}/cover.png"
        _upload_asset(data, object_path)
        _finish_asset(job, object_path, provider_meta)
        return True
    except Exception as exc:
        print(
            "content_asset_error",
            {
                "idea_flow_id": job.get("idea_flow_id"),
                "exception_type": type(exc).__name__,
            },
        )
        _fail_asset(job, exc)
        return False


def process_asset_job(job_id: str) -> bool:
    job = _claim_asset_job(job_id)
    return _process_claimed_asset(job) if job is not None else False


def process_assets_once() -> int:
    return sum(1 for job in _claim_assets() if _process_claimed_asset(job))


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
