from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from backend.tts_service import (
    DEFAULT_VOICE_PROFILE,
    get_voice_profile,
    synthesize_to_file,
)


def test_aira_profile_is_locked() -> None:
    profile = get_voice_profile(DEFAULT_VOICE_PROFILE)
    assert profile["voice"] == "th-TH-PremwadeeNeural"
    assert profile["rate"] == "-25%"
    assert profile["pitch"] == "+20Hz"


def test_unknown_profile_raises() -> None:
    with pytest.raises(ValueError):
        get_voice_profile("UNKNOWN")


def test_synthesize_rejects_empty_text(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        asyncio.run(synthesize_to_file("   ", tmp_path / "out.mp3"))
