"""Text-to-speech service for SoloForge content rendering."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import edge_tts

DEFAULT_VOICE_PROFILE = "AIRA_THAI_V2"

VOICE_PROFILES: dict[str, dict[str, str]] = {
    "AIRA_THAI_V1": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "-25%",
        "pitch": "+20Hz",
        "language": "th-TH",
    },
    "AIRA_THAI_V2": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "-15%",
        "pitch": "+5Hz",
        "language": "th-TH",
    },
}


def get_voice_profile(profile_id: str = DEFAULT_VOICE_PROFILE) -> dict[str, str]:
    """Return a copy of a configured SoloForge voice profile."""
    try:
        return dict(VOICE_PROFILES[profile_id])
    except KeyError as exc:
        raise ValueError(f"Unknown voice profile: {profile_id}") from exc


async def synthesize_to_file(
    text: str,
    output_path: str | Path,
    *,
    profile_id: str = DEFAULT_VOICE_PROFILE,
) -> Path:
    """Generate an MP3 voiceover with Edge TTS and return the output path."""
    normalized = " ".join((text or "").split())
    if not normalized:
        raise ValueError("TTS text is empty")

    profile = get_voice_profile(profile_id)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text=normalized,
        voice=profile["voice"],
        rate=profile["rate"],
        pitch=profile["pitch"],
    )
    await communicate.save(str(output))

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Edge TTS did not create an audio file")
    return output


def _srt_timestamp(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _join_tts_tokens(tokens: list[str]) -> str:
    text = ""
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        if not text:
            text = token
            continue
        prev_ascii = bool(re.search(r"[A-Za-z0-9]$", text))
        next_ascii = bool(re.match(r"^[A-Za-z0-9]", token))
        mixed_boundary = prev_ascii != next_ascii
        text += (" " if (prev_ascii and next_ascii) or mixed_boundary else "") + token
    return text.strip()


def _boundaries_to_srt(boundaries: list[dict[str, object]], max_chars: int = 34,
                       max_duration: float = 2.6, max_tokens: int = 6) -> str:
    groups: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for item in boundaries:
        if item.get("type") != "WordBoundary":
            continue
        candidate = current + [item]
        candidate_text = _join_tts_tokens([str(x.get("text") or "") for x in candidate])
        start = float(candidate[0]["offset"]) / 10_000_000
        end = (float(candidate[-1]["offset"]) + float(candidate[-1]["duration"])) / 10_000_000
        if current and (len(candidate_text) > max_chars or end - start > max_duration or len(candidate) > max_tokens):
            groups.append(current)
            current = [item]
        else:
            current = candidate
    if current:
        groups.append(current)

    blocks: list[str] = []
    for idx, group in enumerate(groups, start=1):
        start = float(group[0]["offset"]) / 10_000_000
        end = (float(group[-1]["offset"]) + float(group[-1]["duration"])) / 10_000_000
        text = _join_tts_tokens([str(x.get("text") or "") for x in group])
        blocks.append(
            f"{idx}\n{_srt_timestamp(start)} --> {_srt_timestamp(end)}\n{text}\n"
        )
    return "\n".join(blocks)


async def synthesize_with_subtitles_to_file(
    text: str,
    output_path: str | Path,
    subtitle_path: str | Path,
    *,
    profile_id: str = DEFAULT_VOICE_PROFILE,
) -> tuple[Path, Path]:
    """Generate audio and SRT from the same Edge TTS stream for exact timing."""
    normalized = " ".join((text or "").split())
    if not normalized:
        raise ValueError("TTS text is empty")

    profile = get_voice_profile(profile_id)
    output = Path(output_path)
    subtitles = Path(subtitle_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    subtitles.parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(
        text=normalized,
        voice=profile["voice"],
        rate=profile["rate"],
        pitch=profile["pitch"],
    )
    boundaries: list[dict[str, object]] = []
    with output.open("wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append(dict(chunk))

    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError("Edge TTS did not create an audio file")
    if not boundaries:
        raise RuntimeError("Edge TTS did not return word boundaries")

    subtitles.write_text(_boundaries_to_srt(boundaries), encoding="utf-8")
    return output, subtitles


def synthesize_with_subtitles_to_file_sync(
    text: str,
    output_path: str | Path,
    subtitle_path: str | Path,
    *,
    profile_id: str = DEFAULT_VOICE_PROFILE,
) -> tuple[Path, Path]:
    return asyncio.run(
        synthesize_with_subtitles_to_file(
            text, output_path, subtitle_path, profile_id=profile_id
        )
    )


async def synthesize_to_bytes(
    text: str,
    *,
    profile_id: str = DEFAULT_VOICE_PROFILE,
) -> bytes:
    """Generate an MP3 voiceover and return its bytes."""
    with NamedTemporaryFile(prefix="soloforge_tts_", suffix=".mp3", delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        await synthesize_to_file(text, temp_path, profile_id=profile_id)
        return temp_path.read_bytes()
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def synthesize_to_file_sync(
    text: str,
    output_path: str | Path,
    *,
    profile_id: str = DEFAULT_VOICE_PROFILE,
) -> Path:
    """Sync wrapper for worker code that runs outside an event loop."""
    return asyncio.run(
        synthesize_to_file(text, output_path, profile_id=profile_id)
    )


def aira_enabled() -> bool:
    """Allow deployments to disable TTS without changing code."""
    return os.getenv("SOLOFORGE_TTS_ENABLED", "1").strip().lower() not in {
        "0", "false", "no", "off"
    }
