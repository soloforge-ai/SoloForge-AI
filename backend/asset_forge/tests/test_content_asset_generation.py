from __future__ import annotations

from backend.asset_forge.backend import content_asset_generation


def test_video_asset_quality_gate_accepts_ai_generated_visual() -> None:
    assert content_asset_generation._video_asset_is_publishable(
        {"provider": "pollinations", "mode": "ai_generated"}
    )


def test_video_asset_quality_gate_rejects_local_template() -> None:
    assert not content_asset_generation._video_asset_is_publishable(
        {"provider": "local_template", "mode": "deterministic_fallback"}
    )


def test_finish_asset_blocks_video_local_template_fallback(monkeypatch) -> None:
    calls = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append((method, path, body, prefer))
        return None

    monkeypatch.setattr(
        content_asset_generation,
        "_supabase_request",
        fake_request,
    )

    content_asset_generation._finish_asset(
        {
            "id": "job-1",
            "content_package": {"pipeline_route": "VIDEO"},
        },
        "job-1/cover.png",
        {
            "provider": "local_template",
            "mode": "deterministic_fallback",
            "attempts": [
                {"provider": "pollinations", "result": "failed"},
                {"provider": "local_template", "result": "success"},
            ],
        },
    )

    assert len(calls) == 1
    _, path, body, _ = calls[0]
    assert "status=eq.ASSET_GENERATING" in path
    assert body["status"] == "ASSET_FAILED"
    assert body["qa_status"] == "FAIL"
    assert body["content_package"]["asset_status"] == "FAILED"
    assert body["content_package"]["asset_quality_gate"]["status"] == "FAIL"
    assert "text-card video" in body["error_message"]


def test_finish_asset_allows_ai_visual_for_video(monkeypatch) -> None:
    calls = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append((method, path, body, prefer))
        return None

    monkeypatch.setattr(
        content_asset_generation,
        "_supabase_request",
        fake_request,
    )

    content_asset_generation._finish_asset(
        {
            "id": "job-2",
            "content_package": {"pipeline_route": "VIDEO"},
        },
        "job-2/cover.png",
        {
            "provider": "pollinations",
            "mode": "ai_generated",
            "attempts": [{"provider": "pollinations", "result": "success"}],
        },
    )

    assert len(calls) == 1
    _, _, body, _ = calls[0]
    assert body["status"] == "ASSET_READY"
    assert body["qa_status"] == "PASS"
    assert body["content_package"]["asset_status"] == "READY"
