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
    assert body["content_package"]["asset_quality_gate"]["result"] == "FAIL"
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



def test_video_asset_quality_gate_accepts_grounded_product_visual() -> None:
    assert content_asset_generation._video_asset_is_publishable(
        {"provider": "product_source", "mode": "product_grounded"}
    )


def test_commercial_asset_uses_grounded_product_image(monkeypatch) -> None:
    calls = {"generated": 0, "downloaded": 0, "finished": 0}

    def fail_generate(*args, **kwargs):
        calls["generated"] += 1
        raise AssertionError("AI generation must not run for grounded commercial product jobs")

    def fake_download(url):
        calls["downloaded"] += 1
        assert url == "https://down-th.img.susercontent.com/product.jpg"
        return b"image-bytes", {
            "provider": "product_source",
            "mode": "product_grounded",
            "provider_version": "product_grounding_v0.1",
            "source_url": url,
            "source_sha256": "abc123",
        }

    monkeypatch.setattr(content_asset_generation, "generate_asset", fail_generate)
    monkeypatch.setattr(
        content_asset_generation,
        "validate_product_grounding",
        lambda package: {
            "canonical_title": "Product",
            "image_urls": ["https://down-th.img.susercontent.com/product.jpg"],
            "identity_status": "LOCKED",
        },
    )
    monkeypatch.setattr(
        content_asset_generation,
        "download_grounded_product_image",
        fake_download,
    )
    monkeypatch.setattr(
        content_asset_generation,
        "stamp_image_bytes",
        lambda data: (data, {"brand_applied": True}),
    )
    monkeypatch.setattr(content_asset_generation, "_upload_asset", lambda *args: None)

    def fake_finish(job, object_path, provider_meta):
        calls["finished"] += 1
        assert object_path == "job-commercial/cover.png"
        assert provider_meta["provider"] == "product_source"
        assert provider_meta["mode"] == "product_grounded"
        assert provider_meta["product_identity_status"] == "LOCKED"

    monkeypatch.setattr(content_asset_generation, "_finish_asset", fake_finish)

    result = content_asset_generation._process_claimed_asset(
        {
            "id": "job-commercial",
            "idea": "Affiliate product post",
            "content_package": {
                "goal": "conversion",
                "pipeline_route": "VIDEO",
                "product_grounding": {
                    "canonical_title": "Product",
                    "image_urls": ["https://down-th.img.susercontent.com/product.jpg"],
                },
            },
        }
    )

    assert result is True
    assert calls == {"generated": 0, "downloaded": 1, "finished": 1}


def test_product_grounding_error_is_not_retried(monkeypatch) -> None:
    calls = []

    def fake_request(method, path, body=None, prefer=None, **kwargs):
        calls.append((method, path, body, prefer))
        return None

    monkeypatch.setattr(content_asset_generation, "_supabase_request", fake_request)

    content_asset_generation._fail_asset(
        {
            "id": "job-grounding-fail",
            "retry_count": 0,
            "content_package": {"goal": "conversion"},
        },
        content_asset_generation.ProductGroundingError("Product image required"),
    )

    assert len(calls) == 1
    _, _, body, _ = calls[0]
    assert body["status"] == "ASSET_FAILED"
    assert body["retry_count"] == 1
    assert body["content_package"]["asset_status"] == "FAILED"
    assert body["content_package"]["product_grounding_status"] == "BLOCKED"
