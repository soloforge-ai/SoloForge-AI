"""Final video renderer for SoloForge content jobs."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

AUDIO_BUCKET = "content-audio"
VIDEO_BUCKET = "content-video"
RENDER_VERSION = "final_render_v0.3_audio_subtitles"


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _supabase_request(method: str, path: str, body: dict[str, object] | None = None,
                      prefer: str | None = None) -> Any:
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
    req = urllib.request.Request(
        f"{base_url}/rest/v1/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        print("render_worker_supabase_http_error", {"status": exc.code, "method": method})
        raise RuntimeError("Content storage unavailable") from exc
    return json.loads(raw.decode("utf-8")) if raw else None


def _storage_download(bucket: str, object_path: str, destination: Path) -> None:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    req = urllib.request.Request(
        f"{base_url}/storage/v1/object/{bucket}/{encoded_path}",
        headers={"apikey": secret_key, "Authorization": f"Bearer {secret_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            destination.write_bytes(response.read())
    except Exception as exc:
        raise RuntimeError("Storage download failed") from exc


def _download_url(url: str, destination: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "SoloForge-Final-Renderer/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            destination.write_bytes(response.read())
    except Exception as exc:
        raise RuntimeError("Base video download failed") from exc


def create_signed_video_url(job_id: str, expires_in: int = 600) -> str:
    """Create a short-lived signed URL for a finished private content video."""
    encoded_job_id = urllib.parse.quote(job_id, safe="")
    rows = _supabase_request(
        "GET",
        f"content_jobs?id=eq.{encoded_job_id}&status=eq.READY_TO_PUBLISH"
        "&select=video_storage_path&limit=1",
    ) or []
    if not rows or not rows[0].get("video_storage_path"):
        raise ValueError("Final video is not ready")

    object_path = str(rows[0]["video_storage_path"])
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    payload = json.dumps({"expiresIn": max(60, min(int(expires_in), 3600))}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/storage/v1/object/sign/{VIDEO_BUCKET}/{encoded_path}",
        data=payload,
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Could not create signed final-video URL") from exc

    signed = body.get("signedURL") or body.get("signedUrl")
    if not signed:
        raise RuntimeError("Supabase did not return a signed URL")
    return signed if str(signed).startswith("http") else f"{base_url}/storage/v1{signed}"


def _storage_upload(bucket: str, object_path: str, local_path: Path, content_type: str) -> None:
    base_url = _required_env("SUPABASE_URL").rstrip("/")
    secret_key = _required_env("SUPABASE_SECRET_KEY")
    encoded_path = urllib.parse.quote(object_path, safe="/")
    req = urllib.request.Request(
        f"{base_url}/storage/v1/object/{bucket}/{encoded_path}",
        data=local_path.read_bytes(),
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": content_type,
            "x-upsert": "true",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            response.read()
    except Exception as exc:
        raise RuntimeError("Storage upload failed") from exc


def _duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _split_script(script: str, max_chars: int = 34) -> list[str]:
    """Split narration into subtitle-sized phrases while preserving authored line breaks."""
    raw = (script or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not raw:
        return []

    logical_lines = [line.strip() for line in raw.split("\n") if line.strip()]
    chunks: list[str] = []

    for line in logical_lines:
        clauses = [
            part.strip()
            for part in re.split(r"(?<=[.!?。！？])\s*|\s*[—–;:]\s*", line)
            if part.strip()
        ]
        for clause in clauses:
            if len(clause) <= max_chars:
                chunks.append(clause)
                continue

            words = clause.split()
            if len(words) <= 1:
                # Thai often has no spaces. Fall back to character windows rather than
                # allowing one subtitle to cover the entire screen.
                chunks.extend(
                    clause[i:i + max_chars].strip()
                    for i in range(0, len(clause), max_chars)
                    if clause[i:i + max_chars].strip()
                )
                continue

            current: list[str] = []
            for word in words:
                candidate = " ".join(current + [word])
                if current and len(candidate) > max_chars:
                    chunks.append(" ".join(current))
                    current = [word]
                else:
                    current.append(word)
            if current:
                chunks.append(" ".join(current))

    return chunks


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _write_srt(script: str, duration: float, path: Path) -> int:
    chunks = _split_script(script)
    if not chunks:
        raise ValueError("Script is empty")
    weights = [max(len(c), 1) for c in chunks]
    total = sum(weights)
    cursor = 0.0
    blocks = []
    for idx, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        share = max(duration * weight / total, 1.2)
        end = min(duration, cursor + share)
        if idx == len(chunks):
            end = duration
        blocks.append(
            f"{idx}\n{_srt_timestamp(cursor)} --> {_srt_timestamp(end)}\n{chunk}\n"
        )
        cursor = end
    path.write_text("\n".join(blocks), encoding="utf-8")
    return len(chunks)


def _recover_stale_rendering(stale_minutes: int = 10) -> int:
    cutoff = datetime.now(timezone.utc).timestamp() - (stale_minutes * 60)
    cutoff_iso = datetime.fromtimestamp(cutoff, timezone.utc).isoformat()
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.FINAL_RENDERING"
        "&render_status=eq.RENDERING"
        f"&updated_at=lt.{urllib.parse.quote(cutoff_iso, safe='')}"
        "&select=id,retry_count",
    ) or []
    recovered = 0
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        retry_count = int(row.get("retry_count") or 0) + 1
        next_status = "AUDIO_READY" if retry_count <= 2 else "RENDER_FAILED"
        _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.FINAL_RENDERING",
            body={
                "status": next_status,
                "render_status": "PENDING" if next_status == "AUDIO_READY" else "FAILED",
                "retry_count": retry_count,
                "error_message": "Recovered stale render after worker restart/OOM",
            },
        )
        recovered += 1
    return recovered


def _claim_ready(limit: int = 1) -> list[dict[str, Any]]:
    rows = _supabase_request(
        "GET",
        "content_jobs?status=eq.AUDIO_READY"
        "&select=id,idea_flow_id,script,video_url,audio_storage_path,retry_count"
        f"&order=updated_at.asc&limit={limit}",
    ) or []
    claimed: list[dict[str, Any]] = []
    for row in rows:
        job_id = urllib.parse.quote(str(row["id"]), safe="")
        if not row.get("video_url"):
            _supabase_request(
                "PATCH",
                f"content_jobs?id=eq.{job_id}&status=eq.AUDIO_READY",
                body={
                    "render_status": "BLOCKED_NO_VIDEO",
                    "render_mode": "WAITING_FOR_BASE_VIDEO",
                    "render_qa": {
                        "status": "BLOCKED",
                        "reason": "video_url is required before final render",
                    },
                },
            )
            continue
        updated = _supabase_request(
            "PATCH",
            f"content_jobs?id=eq.{job_id}&status=eq.AUDIO_READY",
            body={
                "status": "FINAL_RENDERING",
                "render_status": "RENDERING",
                "render_mode": "MUX_VOICE_AND_SUBTITLES",
                "error_message": None,
            },
            prefer="return=representation",
        ) or []
        if updated:
            claimed.append(dict(updated[0]))
    return claimed


def _finish(job: dict[str, Any], object_path: str, qa: dict[str, Any]) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}&status=eq.FINAL_RENDERING",
        body={
            "status": "READY_TO_PUBLISH",
            "render_status": "READY",
            "video_storage_path": object_path,
            "render_generated_at": datetime.now(timezone.utc).isoformat(),
            "render_qa": qa,
            "qa_status": "PASS",
            "error_message": None,
        },
    )


def _fail(job: dict[str, Any], exc: Exception) -> None:
    job_id = urllib.parse.quote(str(job["id"]), safe="")
    retry_count = int(job.get("retry_count") or 0) + 1
    status = "AUDIO_READY" if retry_count <= 2 else "RENDER_FAILED"
    _supabase_request(
        "PATCH",
        f"content_jobs?id=eq.{job_id}",
        body={
            "status": status,
            "render_status": "PENDING" if status == "AUDIO_READY" else "FAILED",
            "retry_count": retry_count,
            "error_message": f"{type(exc).__name__}: {str(exc)[:500]}",
        },
    )


def process_audio_ready_once() -> int:
    try:
        _recover_stale_rendering()
    except Exception as exc:
        print("final_render_recovery_error", {"exception_type": type(exc).__name__})
    processed = 0
    for job in _claim_ready():
        try:
            if not job.get("audio_storage_path"):
                raise ValueError("audio_storage_path is missing")
            with TemporaryDirectory(prefix="soloforge_render_") as tmp:
                root = Path(tmp)
                base_video = root / "base.mp4"
                audio = root / "voice.mp3"
                srt = root / "subs.srt"
                output = root / "final.mp4"

                _download_url(str(job["video_url"]), base_video)
                _storage_download(AUDIO_BUCKET, str(job["audio_storage_path"]), audio)

                audio_duration = _duration(audio)
                subtitle_count = _write_srt(str(job.get("script") or ""), audio_duration, srt)

                style = (
                    "FontName=Noto Sans Thai,FontSize=16,"
                    "PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                    "BackColour=&H50000000,BorderStyle=3,Outline=1,Shadow=0,"
                    "Alignment=2,MarginL=34,MarginR=34,MarginV=110"
                )
                video_filter = (
                    "scale=720:1280:force_original_aspect_ratio=increase,"
                    "crop=720:1280,"
                    f"subtitles={srt}:force_style='{style}',"
                    "format=yuv420p"
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-threads", "1",
                        "-stream_loop", "-1", "-i", str(base_video),
                        "-i", str(audio),
                        "-vf", video_filter,
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-t", f"{audio_duration:.3f}",
                        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
                        "-threads", "1",
                        "-af", "aresample=48000,alimiter=limit=0.90",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                        "-movflags", "+faststart",
                        str(output),
                    ],
                    check=True,
                    capture_output=True,
                )

                video_duration = _duration(output)
                qa = {
                    "status": "PASS",
                    "render_version": RENDER_VERSION,
                    "audio_duration_sec": round(audio_duration, 2),
                    "video_duration_sec": round(video_duration, 2),
                    "subtitle_segments": subtitle_count,
                    "subtitle_layout": "lower_third",
                    "resolution": "720x1280",
                    "render_profile": "EXPERIMENT_LOW_MEMORY",
                    "ffmpeg_threads": 1,
                    "audio_present": True,
                    "audio_codec": "aac_160k_48khz_limited",
                    "duration_delta_sec": round(abs(video_duration - audio_duration), 2),
                }
                if abs(video_duration - audio_duration) > 1.5:
                    raise RuntimeError("Final video duration does not match voiceover")

                object_path = f"{job['id']}/final.mp4"
                _storage_upload(VIDEO_BUCKET, object_path, output, "video/mp4")

            _finish(job, object_path, qa)
            processed += 1
        except Exception as exc:
            print("final_render_error", {
                "idea_flow_id": job.get("idea_flow_id"),
                "exception_type": type(exc).__name__,
            })
            _fail(job, exc)
    return processed


async def final_render_worker_loop() -> None:
    await asyncio.sleep(8)
    while True:
        try:
            await asyncio.to_thread(process_audio_ready_once)
        except Exception as exc:
            print("final_render_worker_loop_error", {"exception_type": type(exc).__name__})
        await asyncio.sleep(30)
