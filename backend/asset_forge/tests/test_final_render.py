from __future__ import annotations

from pathlib import Path

from backend.final_render import _split_script, _write_srt


def test_split_script_falls_back_to_short_chunks() -> None:
    chunks = _split_script("หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด เก้า สิบ สิบเอ็ด")
    assert len(chunks) == 2
    assert chunks[0].startswith("หนึ่ง")


def test_write_srt_covers_audio_duration(tmp_path: Path) -> None:
    path = tmp_path / "subs.srt"
    count = _write_srt(
        "ประโยคหนึ่งสำหรับทดสอบ subtitle ประโยคสองสำหรับทดสอบเวลา",
        6.0,
        path,
    )
    content = path.read_text(encoding="utf-8")
    assert count >= 1
    assert "00:00:06,000" in content
    assert "ประโยค" in content
