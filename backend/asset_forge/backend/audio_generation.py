"""Autonomous Aira TTS worker for approved SoloForge content jobs."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.tts_service import (
    DEFAULT_VOICE_PROFILE,
    aira_enabled,
    synthesize_to_file_sync,
)

AUDIO_BUCKET = "content-audio"
AUDIO_WORKER_VERSION = "content_audio_v0.1"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _supabase_request(
    method: str,
    path: str,
    body: dict[str, object] | None = None,
    prefer: str | None = None,
) -> Any:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    headers = {
        "apikey": secret_key,
        "Authorization": f"Bearer {secret_key}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if prefer:
        headers["Prefer"] = prefer
    request = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print("audio_worker_supabase_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("Content storage unavailable") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Content storage unavailable") from exc
    return json.loads(raw.decode("utf-8")) if raw else None


def _send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_ALLOWED_CHAT_ID", "").strip()
    if not token or not chat_id:
        return
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            response.read()
    except Exception as exc:
        print("audio_worker_telegram_error", {"exception_type": type(exc).__name__})


def _claim_approved(limit: int = 2) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.APPROVED"
        "&select=id,idea_flow_id,script,retry_count,voice_profile"
        f"&order=updated_at.asc&limit={limit}",
    ) or []

    claimed: list[dict[str, Any]] = []
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.APPROVED",
            body={
                "status": "AUDIO_GENERATING",
                "audio_status": "GENERATING",
                "voice_profile": str(row.get("voice_profile") or DEFAULT_VOICE_PROFILE),
                "error_message": None,
            },
            prefer="return=representation",
        ) or []
        if updated:
            claimed.append(dict(updated[0]))
    return claimed


def _upload_audio(local_path: Path, object_path: str) -> None:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    request = urllib.request.Request(
        f"{base_url}/storage/v1/object/{AUDIO_BUCKET}/{encoded_path}",
        data=local_path.read_bytes(),
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "audio/mpeg",
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        print("audio_worker_storage_http_error", {"status": exc.code})
        raise RuntimeError("Audio upload failed") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Audio upload failed") from exc


def _finish_audio(job: dict[str, Any], storage_path: str) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}&status=eq.AUDIO_GENERATING",
        body={
            "status": "AUDIO_READY",
            "audio_status": "READY",
            "audio_storage_path": storage_path,
            "voice_profile": str(job.get("voice_profile") or DEFAULT_VOICE_PROFILE),
            "audio_generated_at": None,
            "error_message": None,
        },
    )


def _fail_audio(job: dict[str, Any], exc: Exception) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    retry_count = int(job.get("retry_count") or 0) + 1
    status = "APPROVED" if retry_count <= 2 else "AUDIO_FAILED"
    audio_status = "PENDING" if status == "APPROVED" else "FAILED"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={
            "status": status,
            "audio_status": audio_status,
            "retry_count": retry_count,
            "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
        },
    )


def process_approved_once() -> int:
    if not aira_enabled():
        return 0

    processed = 0
    for job in _claim_approved():
        idea_id = job.get("idea_flow_id") or "?"
        try:
            script = str(job.get("script") or "").strip()
            if not script:
                raise ValueError("Approved content job has no script")

            profile_id = str(job.get("voice_profile") or DEFAULT_VOICE_PROFILE)
            with TemporaryDirectory(prefix="soloforge_audio_") as tmp:
                local_path = Path(tmp) / "voice.mp3"
                synthesize_to_file_sync(script, local_path, profile_id=profile_id)
                storage_path = f"{job['id']}/{profile_id}.mp3"
                _upload_audio(local_path, storage_path)

            _finish_audio(job, storage_path)
            _send_telegram(
                f"🎙️ Job #{idea_id} — AUDIO_READY\n"
                f"Voice: {profile_id}\n\n"
                f"ขั้นต่อไป: Final Render"
            )
            processed += 1
        except Exception as exc:
            print("content_audio_error", {
                "idea_flow_id": idea_id,
                "exception_type": type(exc).__name__,
            })
            _fail_audio(job, exc)
    return processed


async def audio_worker_loop() -> None:
    await asyncio.sleep(5)
    while True:
        try:
            await asyncio.to_thread(process_approved_once)
        except Exception as exc:
            print("audio_worker_loop_error", {"exception_type": type(exc).__name__})
        await asyncio.sleep(30)
