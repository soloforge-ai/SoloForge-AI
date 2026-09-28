"""Publora publishing integration for SoloForge Content Ops."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    from backend.idea_flow_webhook import _supabase_request
except ImportError:
    from backend.asset_forge.backend.idea_flow_webhook import _supabase_request


PUBLORA_API_BASE = "https://api.publora.com/api/v1"
MEDIA_REQUIRED_PLATFORMS = {"instagram", "tiktok", "youtube"}


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _publora_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    api_key = _required_env("PUBLORA_API_KEY")
    headers = {
        "x-publora-key": api_key,
        "Accept": "application/json",
        "User-Agent": "SoloForge-Content-Ops/0.4",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    request = urllib.request.Request(
        f"{PUBLORA_API_BASE}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        message = f"Publora HTTP {exc.code}"
        try:
            payload = json.loads(raw.decode("utf-8"))
            message = str(payload.get("error") or payload.get("message") or message)
        except Exception:
            pass
        raise RuntimeError(message) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Publora is unavailable") from exc

    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Publora returned an invalid response") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Publora returned an unexpected response")
    return payload


def list_connections() -> list[dict[str, Any]]:
    payload = _publora_request("GET", "/platform-connections")
    rows = payload.get("connections") or []
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, dict)]


def compose_post_content(job: dict[str, Any]) -> str:
    caption = str(job.get("caption") or "").strip()
    cta = str(job.get("cta") or "").strip()
    if caption and cta and cta.lower() not in caption.lower():
        return f"{caption}\n\n{cta}".strip()
    if caption:
        return caption
    if cta:
        return cta
    return str(job.get("script") or job.get("idea") or "").strip()


def _platform_name(platform_id: str) -> str:
    return platform_id.split("-", 1)[0].strip().lower()


def validate_platform_selection(
    platform_ids: list[str],
    connections: list[dict[str, Any]],
    *,
    has_media: bool,
) -> None:
    if not platform_ids:
        raise ValueError("Select at least one publishing account")

    active_ids = {
        str(row.get("platformId"))
        for row in connections
        if row.get("connectionStatus") == "active"
        and row.get("tokenStatus") in {None, "valid"}
        and row.get("platformId")
    }
    unknown = [value for value in platform_ids if value not in active_ids]
    if unknown:
        raise ValueError("One or more selected publishing accounts are not active")

    requires_media = [
        value for value in platform_ids
        if _platform_name(value) in MEDIA_REQUIRED_PLATFORMS
    ]
    if requires_media and not has_media:
        names = ", ".join(sorted({_platform_name(value) for value in requires_media}))
        raise ValueError(f"{names} requires an image or video before publishing")


def _signed_storage_url(bucket: str, object_path: str, expires_in: int = 1200) -> str:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    data = json.dumps({"expiresIn": max(300, min(expires_in, 3600))}).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/storage/v1/object/sign/{bucket}/{encoded_path}",
        data=data,
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Could not create media URL") from exc

    signed = payload.get("signedURL") or payload.get("signedUrl")
    if not signed:
        raise RuntimeError("Storage did not return a signed media URL")
    value = str(signed)
    return value if value.startswith("http") else f"{base_url}/storage/v1{value}"


def media_urls_for_job(job: dict[str, Any]) -> list[str]:
    route = str((job.get("content_package") or {}).get("pipeline_route") or "")
    if route == "VIDEO":
        path = str(job.get("video_storage_path") or "").strip()
        return [_signed_storage_url("content-video", path)] if path else []

    package = dict(job.get("content_package") or {})
    path = str(package.get("asset_storage_path") or "").strip()
    return [_signed_storage_url("content-assets", path)] if path else []


def default_platform_ids(
    job: dict[str, Any],
    connections: list[dict[str, Any]],
) -> list[str]:
    targets = {
        str(value).strip().lower()
        for value in (job.get("content_package") or {}).get("target_platforms", [])
        if str(value).strip()
    }
    if not targets:
        fallback = str(job.get("publish_platform") or "").strip().lower()
        if fallback and fallback != "-":
            targets.add(fallback)

    result: list[str] = []
    for row in connections:
        platform_id = str(row.get("platformId") or "")
        if not platform_id:
            continue
        if (
            _platform_name(platform_id) in targets
            and row.get("connectionStatus") == "active"
            and row.get("tokenStatus") in {None, "valid"}
        ):
            result.append(platform_id)
    return result


def submit_to_publora(
    job: dict[str, Any],
    *,
    platform_ids: list[str],
    scheduled_time: datetime,
) -> dict[str, Any]:
    connections = list_connections()
    media_urls = media_urls_for_job(job)
    validate_platform_selection(platform_ids, connections, has_media=bool(media_urls))

    content = compose_post_content(job)
    if not content and not media_urls:
        raise ValueError("Content job has nothing to publish")

    scheduled_utc = scheduled_time.astimezone(timezone.utc)
    if scheduled_utc <= datetime.now(timezone.utc):
        raise ValueError("Scheduled time must be in the future")

    payload: dict[str, Any] = {
        "content": content,
        "platforms": platform_ids,
        "scheduledTime": scheduled_utc.isoformat().replace("+00:00", "Z"),
    }
    if media_urls:
        payload["mediaUrls"] = media_urls

    if any(_platform_name(value) == "tiktok" for value in platform_ids):
        payload["platformSettings"] = {
            "tiktok": {
                "viewerSetting": "PUBLIC_TO_EVERYONE",
                "allowComments": True,
                "allowDuet": True,
                "allowStitch": True,
            }
        }

    job_id = str(job.get("id") or "")
    key = f"soloforge-{job_id}-{int(scheduled_utc.timestamp())}"
    return _publora_request(
        "POST",
        "/create-post",
        body=payload,
        idempotency_key=key,
    )


def publish_now_time() -> datetime:
    # Publora requires a future scheduledTime. A short buffer behaves like "publish now"
    # while avoiding clock-skew and request-latency failures.
    return datetime.now(timezone.utc) + timedelta(seconds=90)


def sync_publishing_once(limit: int = 20) -> int:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.PUBLISHING&publora_post_id=not.is.null"
        "&select=id,publora_post_id,publish_status,content_package"
        f"&order=updated_at.asc&limit={limit}",
    ) or []

    updated_count = 0
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        post_group_id = urllib.parse.quote(str(row["publora_post_id"]), safe="")
        try:
            payload = _publora_request("GET", f"/get-post/{post_group_id}")
            status = str(payload.get("status") or "").lower()
            publish_status = {
                "draft": "PENDING",
                "scheduled": "QUEUED",
                "publishing": "QUEUED",
                "published": "PUBLISHED",
                "failed": "FAILED",
                "partially_published": "FAILED",
            }.get(status, "PENDING")
            body: dict[str, Any] = {
                "publish_status": publish_status,
                "updated_at": _now(),
            }
            if status == "published":
                body.update(
                    {
                        "status": "PUBLISHED",
                        "published_at": _now(),
                        "error_message": None,
                    }
                )
            elif status in {"failed", "partially_published"}:
                error = payload.get("error")
                body.update(
                    {
                        "status": "PUBLISH_FAILED",
                        "error_message": (
                            str(error.get("message"))
                            if isinstance(error, dict) and error.get("message")
                            else f"Publora status: {status}"
                        ),
                    }
                )
            _supabase_request(
                "PATCH",
                f"content_jobs?id=eq.{job_id}&status=eq.PUBLISHING",
                body=body,
            )
            updated_count += 1
        except Exception as exc:
            print(
                "publora_sync_error",
                {
                    "job_id": str(row.get("id")),
                    "exception_type": type(exc).__name__,
                },
            )
    return updated_count


async def publishing_worker_loop() -> None:
    await asyncio.sleep(10)
    while True:
        try:
            await asyncio.to_thread(sync_publishing_once)
        except Exception as exc:
            print(
                "publishing_worker_loop_error",
                {"exception_type": type(exc).__name__},
            )
        await asyncio.sleep(60)
