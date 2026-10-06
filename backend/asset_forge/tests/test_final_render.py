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


def test_split_script_preserves_thai_line_breaks() -> None:
    script = """ปัญหาไม่ได้อยู่ที่ Prompt อย่างเดียว
แต่เรายังไม่ได้ล็อกตัวตนของ Character ให้ชัด
ก่อนเปลี่ยนฉาก ต้องล็อกหน้า ผม รูปร่าง
รวมถึงจุดจำเฉพาะของตัวละคร
ฉากเปลี่ยนได้ แต่ Identity ควรยังเป็นคนเดิม"""
    chunks = _split_script(script)
    assert 5 <= len(chunks) <= 10
    assert all(len(chunk) <= 34 for chunk in chunks)


def test_job_scoped_render_claim_only_targets_requested_job(monkeypatch) -> None:
    from backend import final_render

    calls = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append((method, path, body, prefer))
        if method == "GET":
            return [{
                "id": "job-1",
                "idea_flow_id": None,
                "script": "hello",
                "video_url": None,
                "audio_storage_path": "job-1/voice.mp3",
                "retry_count": 0,
                "content_package": {"asset_storage_path": "job-1/cover.png"},
            }]
        if method == "PATCH":
            return [{"id": "job-1", "status": "FINAL_RENDERING"}]
        raise AssertionError((method, path))

    monkeypatch.setattr(final_render, "_supabase_request", fake_request)

    claimed = final_render._claim_ready_job("job-1")

    assert claimed["status"] == "FINAL_RENDERING"
    assert "id=eq.job-1&status=eq.AUDIO_READY" in calls[0][1]
