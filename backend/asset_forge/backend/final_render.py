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
RENDER_VERSION = "final_render_v0.1"


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


def _split_script(script: str) -> list[str]:
    clean = " ".join((script or "").split())
    if not clean:
        return []
    chunks = [x.strip() for x in re.split(r"(?<=[.!?。！？])\s+|\s{2,}", clean) if x.strip()]
    if len(chunks) <= 1:
        words = clean.split()
        chunks = [" ".join(words[i:i + 10]) for i in range(0, len(words), 10)]
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
                    "FontName=Noto Sans Thai,FontSize=18,"
                    "PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,"
                    "BackColour=&H50000000,BorderStyle=3,Outline=1,Shadow=0,"
                    "Alignment=2,MarginL=50,MarginR=50,MarginV=170"
                )
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-i", str(base_video),
                        "-i", str(audio),
                        "-vf", f"subtitles={srt}:force_style='{style}'",
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                        "-c:a", "aac", "-b:a", "128k",
                        "-shortest", "-movflags", "+faststart",
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
                    "audio_present": True,
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
