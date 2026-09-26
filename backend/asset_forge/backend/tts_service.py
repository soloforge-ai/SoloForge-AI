"""Text-to-speech service for SoloForge content rendering."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import edge_tts

DEFAULT_VOICE_PROFILE = "AIRA_THAI_V1"

VOICE_PROFILES: dict[str, dict[str, str]] = {
    "AIRA_THAI_V1": {
        "voice": "th-TH-PremwadeeNeural",
        "rate": "-25%",
        "pitch": "+20Hz",
        "language": "th-TH",
    }
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
