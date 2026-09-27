from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.tts_service import (
    DEFAULT_VOICE_PROFILE,
    _boundaries_to_srt,
    get_voice_profile,
    synthesize_to_file,
)


def test_default_aira_v2_profile_is_locked() -> None:
    profile = get_voice_profile(DEFAULT_VOICE_PROFILE)
    assert profile["voice"] == "th-TH-PremwadeeNeural"
    assert profile["rate"] == "-15%"
    assert profile["pitch"] == "+5Hz"


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError):
        get_voice_profile("UNKNOWN")


def test_synthesize_rejects_empty_text(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        asyncio.run(synthesize_to_file("   ", tmp_path / "out.mp3"))


def test_word_boundaries_produce_timed_grouped_srt() -> None:
    boundaries = [
        {"type": "WordBoundary", "offset": 0, "duration": 4_000_000, "text": "ปัญหา"},
        {"type": "WordBoundary", "offset": 4_500_000, "duration": 4_000_000, "text": "ไม่ได้"},
        {"type": "WordBoundary", "offset": 9_000_000, "duration": 3_000_000, "text": "อยู่ที่"},
        {"type": "WordBoundary", "offset": 12_500_000, "duration": 4_000_000, "text": "Prompt"},
        {"type": "WordBoundary", "offset": 17_000_000, "duration": 4_000_000, "text": "อย่างเดียว"},
    ]
    srt = _boundaries_to_srt(boundaries, max_chars=18, max_tokens=3)
    assert "00:00:00,000" in srt
    assert "Prompt" in srt
    assert srt.count("-->") >= 2
